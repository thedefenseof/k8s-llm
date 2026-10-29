import json
import requests
import time
import numpy
import csv
import os
import pandas as pd

URL = "http://localhost:8000/v1/chat/completions"
API_KEY = os.getenv("API_KEY")
MODEL = "/models/Qwen--Qwen2.5-0.5B-Instruct"
MAX_TOKENS = 64
RUNS = 3

def run_once(model, prompt):
    # Функция запускает модель один раз, замеряет основные метрики и возвращает словарь с ними
    headers = {"Authorization": f"Bearer {API_KEY}"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "stream_options": {"include_usage": True},
        "temperature": 0,
        "seed": 42,
        "max_tokens": MAX_TOKENS,
    }

    t_start = time.perf_counter()
    response = requests.post(URL, json=payload, headers=headers, stream=True, timeout=600)
    response.raise_for_status()

    t_first = None
    t_last = None
    usage = None

    for line in response.iter_lines():
        if not line:
            continue
        line = line.decode("utf-8")
        if not line.startswith("data: "):
            continue
        data = line[len("data: "):]
        if data == "[DONE]":
            break
        chunk = json.loads(data)

        if chunk.get("usage"):
            usage = chunk["usage"]
        if chunk["choices"]:
            text = chunk["choices"][0]["delta"].get("content")
            if text:
                now = time.perf_counter()
                if t_first is None:
                    t_first = now
                t_last = now

    ttft = t_first - t_start
    latency = t_last - t_start
    output_tokens = usage["completion_tokens"]
    tok_per_s = (output_tokens - 1) / (t_last - t_first)

    return {
        "ttft": ttft,
        "latency": latency,
        "tok_per_s": tok_per_s,
        "prompt_tokens": usage["prompt_tokens"],
        "output_tokens": output_tokens,
    }

def save_row(row, filename):
# Функция заводит csv файл (если его нет) и записывает в него метрики модели после одного запроса    
    file_exists = os.path.exists(filename)

    with open(filename, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not file_exists:
            writer.writeheader()      
        writer.writerow(row)   

# Набор промптов разной длины для тестирования модели
prompts = {
    'short_1': 'Tell me what is DDL in SQL',
    'short_2': 'Explain difference between DWH and DataLake',
    'short_3': 'Describe who is data engineer',
    'medium_1': '''Tell me what skills are needed to work in a team: 
                We are the Machine Learning Technology Research team. We are engaged in data analysis and machine learning for threat detection tasks: phishing, spam, malware, suspicious activity in corporate networks, and so on. 
                We also implement machine learning technologies (including those based on LLM) in our products and carry out projects to optimize the company’s business processes. 
                Among our projects is the Kaspersky LLM Service, an internal service based on large language models for the secure processing of confidential data.
                We are looking for those who want to learn:
                1. Support large language model inference services
                2. Research benchmarking and performance optimization capabilities of LLMs
                3. Build informative dashboards and analyze service performance
                4. Select optimal LLMs based on the tasks being performed and available resources
                5. Study Azure DevOps pipelines, OpenShift, Kubernetes, Docker''',
    'medium_2': '''Analyze the composition of the chips and provide consumption recommendations: 
                Potatoes, vegetable oil, flavoring (salt, flavoring agents (onion powder, parsley leaves, garlic powder, cheese powder, sour cream powder), whey powder, sucrose, flavor enhancer (monosodium glutamate 1-substituted)).
                The product may contain a small amount of fish and/or seafood powder.
                Ready to use
                Nutritional value per 100 g:
                • Proteins – 6 g
                • Fats – 30 g
                • Carbohydrates – 53 g
                Energy value per 100 g: 510 kcal
                Energy value of 1 pack: 255 kcal''',
    'medium_3': '''Solve the riddle and explain the solution: 
                You enter an old, abandoned, haunted house. It has neither electricity nor running water. Once inside, you see three doors in front of you. Each door has a number on it. 
                Behind each door, there is one way to die. Behind door number one, you will die because there is a lion inside and it will eat you. Behind door number two, you will die because there is a zombie inside and it will attack you. 
                Behind door number three, you will die in the electric chair.
                You have no way to turn back, so you must go through some door. Which door will you go through?''',
    'long_1': '''Analyze the songs texts: one way ticket
                I disappear often
                What’s on my mind? No one knows
                Every gesture scares me (Ah)
                Know that I’m gone (Please-ee)
                While I’m breathing, kiss me
                My thoughts are in closets on the seats
                Ready to fall — cruise altitude
                The day when we’ll never meet again
                While I’m breathing, kiss me-me 
                I disappear often. What’s on my mind? No one knows. 
                Every gesture scares me (Ah). 
                Know that I’m gone (Please‑uh‑uh). 
                While I’m breathing, kiss me. 
                My thoughts are in closets on the sidelines. 
                Ready to fall — cruise altitude. 
                The day when we’ll never meet again. 
                (While I’m breathing—) While I’m breathing, kiss me.
                My thoughts are in closets, on the sidelines.
                Ready to fall — cruise altitude.
                The day when we will never meet again.
                As long as I’m breathing, kiss me.

                cachalot
                You’re not for everyone, and neither am I.
                Listen to how my skin rustles.
                Faces are grimacing behind the glaciers.
                A drawn‑out cry, child of the sperm whale.
                I have a path — a bad road.
                I don't want to think about the past anymore.
                Falling so many stories
                I don't think I'll have tomorrow.
                You're not talking about everyone, and neither am I.
                I can hear your voice in my emptiness.

                midnight cafe
                You look different, dancing, night cafe 
                Time is sad, we don't have a high beam.
                Time is sad, rain, kiss my face
                Oh, oh (Damn), —Ali
                You won’t understand, but it seems I’ve been kidnapped
                Oh, oh-oh-oh, —Ali
                The music in my ears is affecting me (Damn, ONDA)
                Oh, oh-oh (Damn), —Ali
                You won’t understand, but it seems I’ve been kidnapped (Damn, damn)
                Oh, oh-oh-oh, —Ali
                You won’t understand, but it seems I’ve been kidnapped (Damn, ONDA)
                It’s good to be where we’re not, we’re not there.
                It’s good to be where we’re not, we’re not there.
                It’s good to be where we’re not, we’re not there.
                It’s good to be where we’re not, we’re not there.
                You look different (You look different), dancing, a night café.
                Time is sad (Time is sad), the distant light doesn’t shine for us (Ha).
                Time is sad (Time is sad), it’s raining, kiss my face.
                Damn, ONDA.
                You won’t understand, but it seems I’ve been kidnapped (Damn, damn, ONDA)
                This music in my ears is affecting me (Damn, ONDA)
                You won’t understand, but it seems I’ve been kidnapped (Damn, damn, ONDA)
                You won’t understand, but it seems I’m… (Damn, ONDA)”''',
    'long_2': '''Summarize and put it in simple language:
                Now that you have a clearer understanding of the data sharing and cross-domain
                collaboration models, I’d like to share some key principles that you should keep in
                mind to ensure your distributed data management strategy is successful. I’ll start with
                some high-level advice here, then get deeper into specifics for data domains and data
                providers:
                Avoid data silos.
                The first design principle is to discourage the use of silos or integration hubs
                for data distribution. Data silos require additional transformation steps, which
                makes the chain between provider and consumers longer and much harder to
                manage. In, for example, the data warehouse model, we have to deal with 
                inconsistencies when integrating all the data because bounded contexts often conflict.
                Data providers and data consumers in the data warehouse model are tightly
                coupled, which makes the dependencies much more difficult to manage. 
                Organizations often can’t trust data silos because of data quality issues, corrections, and
                inconsistencies.
                By eliminating data silos for data distribution and using newer and more modern
                forms of data integration and distribution, we avoid teams bypassing the integration obstacles 
                and driving the architecture into an unmanageable point-to-pointarchitecture.
                Connecting your domains using point-to-point interfaces creates exponential 
                complexity and should be avoided at all costs.
                For example, interconnecting 100 applications results in 5,000
                point-to-point connections. For 1,000 applications, there will
                be roughly 500,000 point-to-point connections. Point-to-point
                connections can’t provide the control and agility enterprises
                need because the sheer number of communication channels
                makes it nearly impossible to oversee all dependencies.
                Only capture and modify data at the golden source.
                The second principle is aimed at increasing trust in data. It’s important to ensure
                you’re capturing only unique data from your golden sources before distributing
                any data to other systems. Changes to original data should be made only at the
                golden source within the domain, with approval from the owner. 
                For transparency and trust, it’s important to make your golden sources publicly known, so I
                encourage you to set up a central register or catalog that keeps track of all unique
                golden source systems.
                50 | Chapter 2: Organizing Data Using Data Domains Respect the rules of data ownership.
                When applications consume and use data, they can become new golden sources.
                In this circumstance the data truly has a new context, so there are new facts. This
                brings us to our next principle: when data has been changed and new facts are
                created, new ownership is expected. Simple “syntactic transformations,” such as
                filters, unions, upper- to lowercase conversions, and field renames do not require
                new ownership, since all the facts remain the same. This is strongly linked to
                another foundational principle: don’t distribute any data you don’t own. When
                distributing data that originates in and is owned by another domain, always
                ensure your domain gets approval from that domain.''',
    'long_3': '''Compare this language with SQL and tell me which one is better:
                Data Analysis Expressions (DAX) is the native formula and query language for Microsoft PowerPivot, Power BI Desktop and SQL Server Analysis Services (SSAS) Tabular models. 
                DAX includes some of the functions that are used in Excel formulas with additional functions that are designed to work with relational data and perform dynamic aggregation. 
                It is, in part, an evolution of the Multidimensional Expression (MDX) language developed by Microsoft for Analysis Services multidimensional models (often called cubes) combined with Excel formula functions. 
                It is designed to be simple and easy to learn, while exposing the power and flexibility of PowerPivot and SSAS tabular models.
                The Data Analysis Expressions (DAX) language provides a specialized syntax for querying Analysis Services tabular model. 
                DAX is not a programming language. DAX is primarily a formula language and is also a query language. 
                You can use DAX to define custom calculations for Calculated Columns, Measures, Calculated Tables, Calculation Groups, Custom Format Strings, and filter expressions in role-based security in Tabular models. 
                The same Analysis Services engine for Tabular models is also used in Power BI and Power Pivot for Excel. Power BI also uses DAX for conditional formatting expressions and other dynamic properties of visual components.
                DAX can compute values for seven data types:

                Integer (called Whole Number in Power BI, a signed 64-bit integer)
                Decimal (called Decimal Number in Power BI, a double-precision (64-bit) floating-point number)
                Currency (called Fixed Decimal Number in Power BI, a number with four decimal places and stored internally as an integer divided by 10,000)
                DateTime (called Date/time, Date or Time in Power BI, stored internally as a floating-point number where the integer part represents the date in number of days since 30 December 1899 and the decimal part represents the time in terms of its fraction of a day)
                Boolean (called True/false in Power BI, either the value TRUE or the value FALSE)
                String (called Text in Power BI, a sequence of Unicode (UTF-16) characters, comparisons between strings in DAX are case-insensitive)
                Variant (the type given to a DAX expression that might return a value of different types depending on the conditions)
                The BLOB (binary large object) data type is managed by the Tabular model but cannot be directly manipulated by DAX expressions.
                DAX has a powerful type-handling system so that you do not have to worry much about data types. 
                When you write a DAX expression, the resulting type is based on the type of the terms used in the expression and on the operator used. 
                Type conversion happens automatically during the expression evaluation. 
                However, if an expression might return different data types depending on the conditions, then the data type of the expression is defined as Variant.'''
}

def run_benchmark(model):
    # Функция прогревает модель на тестовом промпте и потом собирает данные о ней, прогоняя по 3 раза по промптам    
    
    # Прогрев модели
    run_once(model, "Say hello")

    # Гоняем модель 3 раза
    for name, text in prompts.items():
        for i in range(1, RUNS + 1): 
            unique_text = f'[{int(time.time())}] {text}'                      
            try:
                result = run_once(model, unique_text)
            except Exception as e:
                print(name, i, 'Ошибка:', type(e).__name__, e)
                continue

            row = {
                'prompt_id': name,
                'run': i,
                'model': model,
                'prompt_tokens': result['prompt_tokens'],
                'output_tokens': result['output_tokens'],
                'ttft': round(result['ttft'], 3),
                'tok_per_s': round(result['tok_per_s'], 3),
                'latency': round(result['latency'], 3)
            }
            save_row(row, 'vllm_stats.csv')
            print(name, i, 'Готово')

if __name__ == "__main__":
    run_benchmark(MODEL)
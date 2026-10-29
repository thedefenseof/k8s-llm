# k8s-llm: vLLM в minikube

Небольшая LLM (Qwen2.5-0.5B-Instruct), запущенная через vLLM (CPU-сборка) в minikube.

## Что внутри

- `downloader/` — образ с initContainer (Python, запуск без root). Один раз скачивает веса с Hugging Face в PVC. При перезапуске пода повторно не качает.
- `k8s/` — манифесты Kubernetes:
  - `pvc.yaml` — том `model-storage` для весов модели;
  - `configmap.yaml` — параметры запуска vLLM (`vllm.yaml`: `max-model-len`, `dtype`, `enforce-eager` и др.) и имя репозитория модели. Менять параметры можно без пересборки образа;
  - `logging-configmap.yaml` — конфиг логирования: в логах остаётся факт запроса (`POST /v1/chat/completions ... 200`), а тексты промптов и ответов не пишутся;
  - `deployment.yaml` — Deployment vLLM с initContainer;
  - `service.yaml` — Service для доступа к vLLM внутри кластера.
- `scripts/smoke_test.py` — один запрос к модели для проверки, что всё работает.
- `scripts/benchmark_vllm.py` — бенчмарк (TTFT, latency, throughput).
- `vllm_stats.csv` — результаты последнего запуска бенчмарка.

Секреты (токен Hugging Face и API-ключ vLLM) хранятся в Kubernetes Secret `llm-secrets` и создаются командой `kubectl`. В репозитории, образе и логах их нет.

## Локальный запуск

Нужны Docker, minikube, kubectl, Python 3 и библиотека `requests`. Команды для PowerShell.

1. Запуск кластера:

   ```powershell
   minikube start
   ```

2. Сборка образа загрузки и загрузка в minikube:

   ```powershell
   docker build -t llm-downloader:0.1 downloader
   minikube image load llm-downloader:0.1
   ```

3. Secret (подставить свои значения):

   ```powershell
   kubectl create secret generic llm-secrets `
     --from-literal=HF_TOKEN=<твой_токен_Hugging_Face> `
     --from-literal=API_KEY=<придуманный_ключ_для_API>
   ```

4. Манифесты:

   ```powershell
   kubectl apply -f k8s/pvc.yaml
   kubectl apply -f k8s/configmap.yaml
   kubectl apply -f k8s/logging-configmap.yaml
   kubectl apply -f k8s/service.yaml
   kubectl apply -f k8s/deployment.yaml
   ```

5. Готово, когда в логах появилась строка `Application startup complete`, а под в статусе `1/1 Running`:

   ```powershell
   kubectl get pods
   kubectl logs deployment/vllm -f
   ```

6. Порт:

   ```powershell
   kubectl port-forward svc/vllm 8000:8000
   ```

7. Проверка запроса в другом окне:

   ```powershell
   $env:API_KEY = "<тот_же_ключ_для_API>"
   py scripts\smoke_test.py
   ```

Изменить параметры vLLM: изменить `vllm.yaml` в `k8s/configmap.yaml`, затем

```powershell
kubectl apply -f k8s/configmap.yaml
kubectl rollout restart deployment/vllm
```

## Бенчмарк

Скрипт `scripts/benchmark_vllm.py` отправляет потоковые запросы (SSE) к работающему vLLM и записывает результаты в `vllm_stats.csv`.
Набор: 9 промптов трёх размеров (short ~48, medium ~207, long ~699 токенов), по 3 прогона на каждый, `max_tokens=64`, запросы идут по одному.
Перед замером делается прогрев. К каждому промпту добавляется уникальный временной префикс, чтобы префиксный кэш не искажал результат.

Запуск (при работающем port-forward):

```powershell
$env:API_KEY = "<ключ_для_API>"
py scripts\benchmark_vllm.py
```

Метрики:
- **TTFT** — время от отправки запроса до первого токена;
- **latency** — полное время до последнего токена;
- **tok_per_s** — скорость генерации: `(output_tokens − 1) / (t_last − t_first)`

## Результаты

Окружение: vLLM 0.29.0 (CPU), Qwen2.5-0.5B-Instruct, `dtype: bfloat16`, `enforce-eager: true`, `max-model-len: 2048`, KV-кэш 1 ГиБ. Среднее по 3 прогонам. В `prompt_tokens` входит ~30 токенов системного промпта Qwen, которые добавляются автоматически.

| prompt_id | prompt_tokens | output_tokens | ttft, с | latency, с | tok_per_s |
|:--|--:|--:|--:|--:|--:|
| short_1 | 49 | 64 | 2.82 | 22.50 | 3.25 |
| short_2 | 49 | 64 | 3.30 | 28.06 | 2.55 |
| short_3 | 46 | 64 | 2.99 | 26.86 | 2.64 |
| medium_1 | 241 | 64 | 12.80 | 39.10 | 2.40 |
| medium_2 | 199 | 64 | 10.10 | 34.35 | 2.60 |
| medium_3 | 182 | 64 | 9.56 | 33.13 | 2.69 |
| long_1 | 726 | 64 | 32.54 | 55.56 | 2.80 |
| long_2 | 707 | 64 | 29.11 | 50.59 | 3.02 |
| long_3 | 663 | 64 | 28.71 | 52.86 | 2.61 |

По группам: short — TTFT 3.0 с, latency 25.8 с; medium — 10.8 с и 35.5 с; long — 30.1 с и 53.0 с. Скорость генерации во всех группах около 2.6–2.8 токена в секунду.

Выводы:
- TTFT растёт почти линейно с длиной промпта. Время до первого токена определяется обработкой промпта (prefill).
- Скорость генерации от длины промпта не зависит. Это скорость самой модели на CPU.
- Latency равна TTFT плюс время генерации (около 20–25 с на 64 токена), поэтому разница между короткими и длинными промптами в latency почти целиком определяется TTFT.

## Что можно изменить в конфигурации для повышения Throughput

**А. Когда идет большой поток запросов с маленьким количеством токенов** 
- `max-num-seqs` — максимум запросов в одном батче; больше значение — больше запросов обслуживается за один проход по модели;
- `VLLM_CPU_KVCACHE_SPACE` — чем он больше, тем больше запросов помещается одновременно;
- `max-model-len` — если его уменьшить, то каждый запрос резервирует меньше памяти;
- префиксный кэш (включён) — одинаковое начало запросов, например системный промпт, считается один раз.

**Б. Когда запросов меньше, но они содержат огромное количество токенов (большой контекст)**
- `max-num-batched-tokens` — больше значение — меньше шагов на длинный промпт, но вырастет нагрузка на память и вычисления;
- chunked prefill (`enable-chunked-prefill`) — длинный промпт режется на части и мешается с другими запросами, тогда короткие запросы не ждут, пока обработается один длинный;
- `max-model-len` — должен покрывать самый длинный промпт плюс ответ;
- KV-кэш нужно увеличить, потому что длинные запросы занимают много места.


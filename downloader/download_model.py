import os
import sys
import shutil
from huggingface_hub import snapshot_download

REPO_ID = os.getenv('REPO_ID')
MODEL_ROOT = os.getenv('MODEL_ROOT', '/models')
HF_TOKEN = os.getenv("HF_TOKEN")  

def main():
    if not REPO_ID:
        print('Ошибка: REPO_ID не задан')
        sys.exit(1)

    model_name = REPO_ID.replace('/', '--')  
    final_dir = os.path.join(MODEL_ROOT, model_name)
    marker = os.path.join(final_dir, '.complete')

    if os.path.exists(marker):
        print(f'Модель {REPO_ID} установлена: {final_dir}')
        return

    os.makedirs(MODEL_ROOT, exist_ok=True)
    tmp_dir = final_dir + '.tmp'

    try:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        shutil.rmtree(final_dir, ignore_errors=True)

        
        print(f"Скачивание {REPO_ID} в {tmp_dir} ...")
        snapshot_download(repo_id=REPO_ID, local_dir=tmp_dir, token=HF_TOKEN)

        open(os.path.join(tmp_dir, ".complete"), "w").close()

        os.replace(tmp_dir, final_dir)
        print(f"Готово: {final_dir}")
    except Exception as e:
        print(f"Ошибка скачивания: {type(e).__name__}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()

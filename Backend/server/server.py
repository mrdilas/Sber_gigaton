# server.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from neyro import GigaChatManager
from pdf_segmenter import process_pdf  # Оставляем для возможного использования
import time
import os
import uuid
import PyPDF2  # Добавьте этот импорт
from supabase import create_client, Client
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB limit

# Конфигурация
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed_files'
ALLOWED_EXTENSIONS = {'pdf'}

# Создаем папки если их нет
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# Инициализация GigaChat
# Укажите собственный API-токен
API_TOKEN = 'MDE5OTlhYjktYzA5My03ZjQzLTk1OTMtMzI5NzVmYTA0OWMyOmY0MjFmYzMwLWY3YzQtNGE2MC04NjMzLWE0MTdjOTY3ZDc3OA=='
giga_manager = GigaChatManager(API_TOKEN)

# Инициализация Supabase 
SUPABASE_URL = 'https://bppgahmqwuduiadqmbbr.supabase.co'  
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJwcGdhaG1xd3VkdWlhZHFtYmJyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1OTE5NDc4NywiZXhwIjoyMDc0NzcwNzg3fQ.3ivMQF3kVj4uP94SwEcnWuM0swAawnVCZmn8QbKJqnQ'
supabase = None

def init_supabase():
    """Инициализация Supabase клиента"""
    global supabase
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Supabase клиент инициализирован")
        
        # Проверяем подключение
        try:
            response = supabase.table('pdf_files').select('id').limit(1).execute()
            print("Подключение к Supabase успешно")
            return True
        except Exception as e:
            print(f"Ошибка проверки подключения: {e}")
            return False
            
    except Exception as e:
        print(f"Ошибка инициализации Supabase: {e}")
        return False

def allowed_file(filename):
    """Проверка расширения файла"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_pdf_to_gigachat(pdf_path):
    """Загрузка PDF файла в GigaChat"""
    try:
        print(f"Загружаем PDF в GigaChat: {pdf_path}")
        giga_manager.upload_file(pdf_path)
        
        files = giga_manager.files
        if files:
            latest_file = files[-1]
            print(f"PDF загружен в GigaChat с ID: {latest_file.id}")
            return latest_file.id
        else:
            raise Exception("Не удалось получить ID загруженного файла")
    except Exception as e:
        print(f"Ошибка загрузки PDF в GigaChat: {e}")
        raise e

def process_pdf_for_search(pdf_path):
    """Дополнительная обработка PDF для внутреннего поиска"""
    try:
        print(f"Создаем текстовую версию для поиска: {pdf_path}")
        txt_path = process_pdf(pdf_path)
        print(f"Текстовая версия создана: {txt_path}")
        return txt_path
    except Exception as e:
        print(f"Ошибка создания текстовой версии: {e}")
        return None

def split_pdf_by_pages(pdf_path, max_pages_per_chunk=50):
    """Разбиваем PDF на части"""
    import PyPDF2
    from pathlib import Path
    
    try:
        pdf_path = Path(pdf_path)
        chunks = []
        
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            
            for start_page in range(0, total_pages, max_pages_per_chunk):
                end_page = min(start_page + max_pages_per_chunk, total_pages)
                
                # Создаем новый PDF с частью страниц
                pdf_writer = PyPDF2.PdfWriter()
                for page_num in range(start_page, end_page):
                    pdf_writer.add_page(pdf_reader.pages[page_num])
                
                chunk_path = pdf_path.parent / f"{pdf_path.stem}_part_{start_page//max_pages_per_chunk + 1}.pdf"
                with open(chunk_path, 'wb') as chunk_file:
                    pdf_writer.write(chunk_file)
                
                chunks.append(chunk_path)
                print(f"Создан чанк: {chunk_path.name} (страницы {start_page+1}-{end_page})")
        
        return chunks
    except Exception as e:
        print(f"Ошибка разбивки PDF на чанки: {e}")
        return []

def upload_pdf_chunks_to_gigachat(pdf_path, max_size_mb=20):
    """Загружаем PDF чанками если файл большой"""
    file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
    
    if file_size_mb <= max_size_mb:
        # Файл небольшой - загружаем как есть
        return upload_pdf_to_gigachat(pdf_path), [pdf_path]
    else:
        # Файл большой - разбиваем на части
        print(f"Файл слишком большой ({file_size_mb:.2f} MB), разбиваем на части...")
        chunks = split_pdf_by_pages(pdf_path)
        chunk_ids = []
        
        for chunk_path in chunks:
            try:
                chunk_id = upload_pdf_to_gigachat(chunk_path)
                chunk_ids.append(chunk_id)
                print(f"Чанк загружен в GigaChat: {chunk_id}")
            except Exception as e:
                print(f"Ошибка загрузки чанка {chunk_path}: {e}")
        
        return chunk_ids, chunks

def create_smart_chunks_from_pdf(pdf_path, max_chunk_size=15000):
    """Создаем умные текстовые чанки из PDF"""
    try:
        txt_path = process_pdf(pdf_path)
        
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Разбиваем на смысловые chunks (по страницам)
        chunks = []
        current_chunk = ""
        
        # Простая логика разбивки по страницам
        pages = content.split('📄 СТРАНИЦА')
        for page in pages[1:]:  # Пропускаем первый элемент (он пустой)
            page_content = '📄 СТРАНИЦА' + page
            
            if len(current_chunk) + len(page_content) > max_chunk_size and current_chunk:
                chunks.append(current_chunk)
                current_chunk = page_content
            else:
                current_chunk += page_content
        
        if current_chunk:
            chunks.append(current_chunk)
        
        print(f"Создано {len(chunks)} текстовых чанков")
        return chunks, txt_path
    except Exception as e:
        print(f"Ошибка создания текстовых чанков: {e}")
        return [], None

def ask_with_context(message, context_chunks):
    """Запрос к GigaChat с контекстом из чанков"""
    try:
        # Выбираем наиболее релевантные чанки (упрощенная версия)
        relevant_chunks = context_chunks[:3]  # Берем первые 3 чанка
        
        context = "\n\n".join(relevant_chunks)
        
        prompt = f"""
        Ты - эксперт в области инженерии и машиностроения.
        Отвечай на вопрос на основе следующего контекста из технического документа:
        
        КОНТЕКСТ ДОКУМЕНТА:
        {context}
        
        ВОПРОС: {message}
        
        Ответь технически грамотно и подробно, ссылаясь на информацию из документа:
        """
        
        result = giga_manager.giga.chat({
            "messages": [{"role": "assistant", "content": prompt}],
            "temperature": 0.87,
            "max-tokens": 1000,

        })
        
        return result
    except Exception as e:
        print(f"Ошибка в ask_with_context: {e}")
        raise e

def upload_pdf_chunks_to_gigachat(pdf_path, max_size_mb=20):
    """Загружаем PDF чанками если файл слишком большой"""
    try:
        file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
        
        if file_size_mb <= max_size_mb:
            # Файл небольшой - загружаем как есть
            file_id = upload_pdf_to_gigachat(pdf_path)
            return [file_id], [pdf_path]
        else:
            # Файл большой - разбиваем на части
            print(f"Файл слишком большой ({file_size_mb:.2f} MB), разбиваем на части...")
            chunks = split_pdf_by_pages(pdf_path)
            chunk_ids = []
            
            for chunk_path in chunks:
                try:
                    chunk_id = upload_pdf_to_gigachat(chunk_path)
                    chunk_ids.append(chunk_id)
                    print(f"Чанк загружен в GigaChat: {chunk_id}")
                except Exception as e:
                    print(f"Ошибка загрузки чанка {chunk_path}: {e}")
            
            return chunk_ids, chunks
    except Exception as e:
        print(f"Ошибка в upload_pdf_chunks_to_gigachat: {e}")
        return [], []




# Эндпоинты
@app.route('/chat', methods=['POST'])
def chat_with_ai():
    try:
        data = request.get_json()

        if not data or 'message' not in data:
            return jsonify({'error': 'Сообщение обязательно'}), 400

        user_message = data['message']
        selected_file = data.get('selected_file_id')

        print(f"Получен selected_file: {selected_file}, тип: {type(selected_file)}")

        # ИЗВЛЕКАЕМ ID ФАЙЛА
        selected_file_id = None
        
        if selected_file:
            if isinstance(selected_file, dict):
                selected_file_id = selected_file.get('id')
                print(f"Извлечен ID из объекта: {selected_file_id}")
            elif isinstance(selected_file, (str, int)):
                selected_file_id = str(selected_file)
                print(f"Используем чистый ID: {selected_file_id}")
            else:
                print(f"Неизвестный формат: {type(selected_file)}")
                selected_file_id = None

        print(f"Окончательный file_id: {selected_file_id}")

        if not user_message.strip():
            return jsonify({'error': 'Сообщение не может быть пустым'}), 400

        # Получаем информацию о файле из базы
        file_info = None
        if selected_file_id:
            try:
                file_response = supabase.table('pdf_files').select('*').eq('id', selected_file_id).execute()
                if file_response.data:
                    file_info = file_response.data[0]
                    print(f"Найден файл в базе: {file_info['name']}")
                else:
                    print(f"Файл с ID {selected_file_id} не найден в базе")
            except Exception as e:
                print(f"Ошибка поиска файла в базе: {e}")

        # Обработка запроса
        start_time = time.time()
        
        if file_info and file_info.get('upload_method') == 'direct' and file_info.get('gigachat_file_id'):
            # Прямой метод с attachments
            gigachat_file_id = file_info['gigachat_file_id']
            print(f"Используем прямой метод с файлом: {gigachat_file_id}")
            
            result = giga_manager.giga.chat({
                "messages": [{
                    "role": "user",
                    "content": f"Ответь на вопрос на основе прикрепленного технического документа: {user_message}",
                    "attachments": [gigachat_file_id],
                }],
                "temperature": 0.1
            })
            
        elif file_info and file_info.get('txt_path'):
            # Метод текстовых чанков
            txt_path = file_info['txt_path']
            print(f"Используем текстовые чанки из: {txt_path}")
            
            try:
                chunks, _ = create_smart_chunks_from_pdf(file_info['storage_path'])
                result = ask_with_context(user_message, chunks)
            except Exception as e:
                print(f"Ошибка использования текстовых чанков: {e}")
                # Fallback - общий запрос
                result = giga_manager.giga.chat({
                    "messages": [{"role": "user", "content": user_message}],
                    "temperature": 0.1
                })
        else:
            # Общий запрос без файла
            print("Используем общий запрос без файла")
            result = giga_manager.giga.chat({
                "messages": [{"role": "user", "content": user_message}],
                "temperature": 0.1
            })

        # Извлекаем ответ
        if hasattr(result, 'choices') and len(result.choices) > 0:
            ai_response = result.choices[0].message.content
        elif hasattr(result, 'message') and hasattr(result.message, 'content'):
            ai_response = result.message.content
        else:
            ai_response = "Не удалось получить ответ от нейросети"

        processing_time = time.time() - start_time

        print(f"Ответ получен за {processing_time:.2f} сек")

        return jsonify({
            'response': ai_response,
            'status': 'success',
            'processing_time': f"{processing_time:.2f} сек",
            'used_file_id': selected_file_id
        })

    except Exception as e:
        print(f"Ошибка при обработке запроса: {e}")
        return jsonify({
            'error': f'Внутренняя ошибка сервера: {str(e)}'
        }), 500

@app.route('/api/pdf/upload', methods=['POST'])
def upload_pdf_file():
    """Загрузка PDF файла с обработкой больших файлов"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Файл обязателен'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
            
        if not allowed_file(file.filename):
            return jsonify({'error': 'Только PDF файлы разрешены'}), 400

        # Сохраняем оригинальный PDF
        original_filename = secure_filename(file.filename)
        pdf_save_path = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4()}_{original_filename}")
        file.save(pdf_save_path)
        
        file_size = os.path.getsize(pdf_save_path)
        file_size_mb = file_size / (1024 * 1024)
        
        print(f"PDF сохранен: {pdf_save_path}, размер: {file_size_mb:.2f} MB")

        gigachat_file_ids = []
        upload_method = "text_chunks"  # По умолчанию используем текстовые чанки
        
        # Пробуем загрузить напрямую если файл маленький
        if file_size_mb <= 20:  # До 20MB
            try:
                file_id = upload_pdf_to_gigachat(pdf_save_path)
                gigachat_file_ids = [file_id]
                upload_method = "direct"
                print(f"Файл загружен напрямую в GigaChat: {file_id}")
            except Exception as e:
                print(f"Прямая загрузка не удалась: {e}")
                upload_method = "text_chunks"
        
        # Создаем текстовую версию для поиска (всегда)
        txt_path = None
        try:
            chunks, txt_path = create_smart_chunks_from_pdf(pdf_save_path)
            print(f"Текстовая версия создана: {txt_path}")
        except Exception as e:
            print(f"Ошибка создания текстовой версии: {e}")
        
        # Сохраняем информацию в Supabase
        file_data = {
            'name': original_filename,
            'storage_path': str(pdf_save_path),
            'file_url': f"/api/files/{os.path.basename(pdf_save_path)}",
            'file_size': file_size,
            'gigachat_file_id': gigachat_file_ids[0] if gigachat_file_ids else None,
            'txt_path': str(txt_path) if txt_path else None,
            'upload_method': upload_method
        }
        
        db_response = supabase.table('pdf_files').insert(file_data).execute()
        
        if not db_response.data:
            raise Exception("Не удалось сохранить данные в базу")

        file_data = db_response.data[0]

        return jsonify({
            'message': f'PDF файл успешно обработан ({upload_method} метод)',
            'file': file_data,
            'file_size_mb': f"{file_size_mb:.2f}",
            'upload_method': upload_method,
            'gigachat_file_id': gigachat_file_ids[0] if gigachat_file_ids else None
        })
        
    except Exception as e:
        print(f"Ошибка при загрузке файла: {e}")
        if 'pdf_save_path' in locals() and os.path.exists(pdf_save_path):
            os.remove(pdf_save_path)
        return jsonify({'error': f'Ошибка обработки: {str(e)}'}), 500

# Остальные эндпоинты остаются без изменений
@app.route('/api/pdf/files', methods=['GET'])
def get_pdf_files_list():
    """Получение списка обработанных файлов из Supabase"""
    try:
        response = supabase.table('pdf_files').select('*').order('uploaded_at').execute()
        
        print(f"Получено файлов: {len(response.data)}")
        for file in response.data:
            print(f"Файл: {file['name']}, GigaChat ID: {file.get('gigachat_file_id', 'N/A')}")
        
        return jsonify({
            'files': response.data,
            'total_count': len(response.data)
        })
        
    except Exception as e:
        print(f"Ошибка получения файлов: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/pdf/delete/<file_id>', methods=['DELETE'])
def delete_pdf_file(file_id):
    """Удаление PDF файла и связанных данных"""
    try:
        # Получаем информацию о файле
        file_response = supabase.table('pdf_files').select('*').eq('id', file_id).execute()
        
        if not file_response.data:
            return jsonify({'error': 'Файл не найден'}), 404
            
        file_data = file_response.data[0]
        gigachat_file_id = file_data.get('gigachat_file_id')
        storage_path = file_data.get('storage_path')
        txt_path = file_data.get('txt_path')

        # Удаляем файл из GigaChat
        if gigachat_file_id:
            try:
                giga_manager.delete_file_by_id(gigachat_file_id)
                print(f"Файл удален из GigaChat: {gigachat_file_id}")
            except Exception as e:
                print(f"Ошибка удаления из GigaChat: {e}")

        # Удаляем локальные файлы
        if storage_path and os.path.exists(storage_path):
            os.remove(storage_path)
        if txt_path and os.path.exists(txt_path):
            os.remove(txt_path)
        
        # Удаляем запись из таблицы
        supabase.table('pdf_files').delete().eq('id', file_id).execute()

        return jsonify({'message': 'Файл успешно удален'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Проверка работоспособности сервера"""
    try:
        files_count = len(giga_manager.files)
        
        supabase_status = "OK"
        
        # Проверяем подключение к Supabase
        if supabase:
            try:
                test_response = supabase.table('pdf_files').select('id').limit(1).execute()
            except Exception as e:
                supabase_status = f"ERROR: {str(e)}"
        else:
            supabase_status = "NOT INITIALIZED"
        
        return jsonify({
            'status': 'OK',
            'message': 'Сервер работает',
            'gigachat_files_available': files_count,
            'supabase_status': supabase_status
        })
    except Exception as e:
        return jsonify({
            'status': 'ERROR',
            'message': f'Ошибка подключения: {str(e)}'
        }), 500

if __name__ == '__main__':
    print("Запуск сервера на http://localhost:5000")
    
    # Проверяем подключение к GigaChat
    try:
        files = giga_manager.files
        print(f"Подключение к GigaChat успешно. Доступно файлов: {len(files)}")
        for file in files:
            print(f"  - {file.fullname} (ID: {file.id})")
    except Exception as e:
        print(f"Ошибка подключения к GigaChat: {e}")

    # Инициализируем Supabase
    supabase_initialized = init_supabase()
    if supabase_initialized:
        print("Подключение к Supabase успешно")
    else:
        print("Ошибка подключения к Supabase")

    app.run(host='0.0.0.0', port=5000, debug=True)
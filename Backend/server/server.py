from flask import Flask, request, jsonify
from flask_cors import CORS
from neyro import GigaChatManager
from supabase import create_client, Client
import time
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# Конфигурация
API_TOKEN = 'MDE5OTc1YzktMTIxZS03NTM1LWEzNDYtNTUyY2Y4ZTMzYzg2OjcwYWJmNTM2LTI0YWEtNGJhMi05N2ZiLWU3YzQzNTVmYWEzYw=='
SUPABASE_URL = 'https://bppgahmqwuduiadqmbbr.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJwcGdhaG1xd3VkdWlhZHFtYmJyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1OTE5NDc4NywiZXhwIjoyMDc0NzcwNzg3fQ.3ivMQF3kVj4uP94SwEcnWuM0swAawnVCZmn8QbKJqnQ'

# Инициализация клиентов
giga_manager = GigaChatManager(API_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    """Проверка расширения файла"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_supabase():
    """Инициализация и проверка подключения к Supabase"""
    try:
        # Проверяем подключение
        response = supabase.table('pdf_files').select('id').limit(1).execute()
        print("✅ Подключение к Supabase успешно")
        return True
    except Exception as e:
        print(f"❌ Ошибка подключения к Supabase: {e}")
        return False

def save_file_to_database(file_data):
    """Сохранение информации о файле в Supabase"""
    try:
        response = supabase.table('pdf_files').insert(file_data).execute()
        
        if response.data:
            print(f"✅ Файл сохранен в базу с ID: {response.data[0]['id']}")
            return response.data[0]
        else:
            raise Exception("Не удалось сохранить данные в базу")
            
    except Exception as e:
        print(f"❌ Ошибка сохранения в базу: {e}")
        raise e

def get_file_from_database(file_id):
    """Получение информации о файле из Supabase"""
    try:
        response = supabase.table('pdf_files').select('*').eq('id', file_id).execute()
        
        if response.data:
            return response.data[0]
        else:
            return None
            
    except Exception as e:
        print(f"❌ Ошибка получения файла из базы: {e}")
        return None

def get_all_files_from_database():
    """Получение всех файлов из Supabase"""
    try:
        response = supabase.table('pdf_files').select('*').order('created_at', desc=True).execute()
        return response.data
    except Exception as e:
        print(f"❌ Ошибка получения файлов из базы: {e}")
        return []

def delete_file_from_database(file_id):
    """Удаление файла из Supabase"""
    try:
        response = supabase.table('pdf_files').delete().eq('id', file_id).execute()
        print(f"✅ Файл удален из базы: {file_id}")
        return True
    except Exception as e:
        print(f"❌ Ошибка удаления файла из базы: {e}")
        return False

# Эндпоинты
@app.route('/api/health', methods=['GET'])
def health_check():
    """Проверка работоспособности сервера"""
    try:
        # Проверяем GigaChat
        gigachat_files = giga_manager.files
        gigachat_status = "OK"
        
        # Проверяем Supabase
        supabase_status = "OK"
        try:
            supabase.table('pdf_files').select('id').limit(1).execute()
        except Exception as e:
            supabase_status = f"ERROR: {str(e)}"
        
        # Получаем статистику из базы
        files_response = supabase.table('pdf_files').select('id', count='exact').execute()
        files_count = files_response.count if hasattr(files_response, 'count') else len(files_response.data)
        
        return jsonify({
            'status': 'OK',
            'message': 'Сервер работает',
            'gigachat': {
                'status': gigachat_status,
                'files_count': len(gigachat_files)
            },
            'supabase': {
                'status': supabase_status,
                'files_count': files_count
            },
            'server_time': time.strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({
            'status': 'ERROR',
            'message': f'Ошибка подключения: {str(e)}'
        }), 500

@app.route('/api/files/upload', methods=['POST'])
def upload_pdf_file():
    """Загрузка и обработка PDF файла"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Файл обязателен'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
            
        if not allowed_file(file.filename):
            return jsonify({'error': 'Только PDF файлы разрешены'}), 400

        # Сохраняем файл во временную память для обработки
        file_content = file.read()
        file_size = len(file_content)
        file_size_mb = file_size / (1024 * 1024)
        
        original_filename = secure_filename(file.filename)
        
        print(f"📄 Начало обработки PDF: {original_filename}, размер: {file_size_mb:.2f} MB")

        # Сохраняем во временный файл для загрузки в GigaChat
        temp_filename = f"temp_{uuid.uuid4()}.pdf"
        with open(temp_filename, 'wb') as temp_file:
            temp_file.write(file_content)

        try:
            # Загружаем PDF файл напрямую в GigaChat
            print(f"📤 Загрузка файла в GigaChat: {original_filename}")
            giga_manager.upload_file(temp_filename)
            
            # Получаем ID загруженного файла
            files = giga_manager.files
            if not files:
                raise Exception("Не удалось получить ID загруженного файла")
                
            latest_file = files[-1]
            gigachat_file_id = latest_file.id
            
            print(f"✅ Файл загружен в GigaChat с ID: {gigachat_file_id}")

            # Сохраняем информацию в Supabase
            file_data = {
                'name': original_filename,
                'file_size': file_size,
                'gigachat_file_id': gigachat_file_id,
                'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            saved_file = save_file_to_database(file_data)

            return jsonify({
                'message': 'PDF файл успешно загружен и обработан',
                'file': saved_file,
                'file_size_mb': round(file_size_mb, 2),
                'status': 'success'
            })
            
        finally:
            # Удаляем временный файл
            import os
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
                print(f"🗑️ Временный файл удален: {temp_filename}")
        
    except Exception as e:
        print(f"❌ Ошибка при загрузке файла: {e}")
        return jsonify({'error': f'Ошибка обработки: {str(e)}'}), 500

@app.route('/api/files', methods=['GET'])
def get_files_list():
    """Получение списка всех обработанных файлов"""
    try:
        files_list = get_all_files_from_database()
        
        print(f"📋 Получен список файлов из базы: {len(files_list)} файлов")
        
        # Добавляем человекочитаемый размер файлов
        for file in files_list:
            file_size_mb = file['file_size'] / (1024 * 1024)
            file['file_size_mb'] = round(file_size_mb, 2)
        
        return jsonify({
            'files': files_list,
            'total_count': len(files_list)
        })
        
    except Exception as e:
        print(f"❌ Ошибка получения файлов: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat_with_ai():
    """Чат с AI на основе загруженных материалов"""
    try:
        data = request.get_json()

        if not data or 'message' not in data:
            return jsonify({'error': 'Сообщение обязательно'}), 400

        user_message = data['message']
        file_id = data.get('file_id')

        print(f"💬 Получен запрос: '{user_message}'")
        print(f"📁 Выбран файл ID: {file_id}")

        if not user_message.strip():
            return jsonify({'error': 'Сообщение не может быть пустым'}), 400

        # Получаем информацию о файле из базы
        file_info = None
        gigachat_file_id = None
        
        if file_id:
            file_info = get_file_from_database(file_id)
            if not file_info:
                return jsonify({'error': 'Файл не найден в базе данных'}), 404
            
            gigachat_file_id = file_info.get('gigachat_file_id')
            print(f"📄 Используем файл: {file_info['name']} (GigaChat ID: {gigachat_file_id})")

        # Обработка запроса
        start_time = time.time()
        
        if gigachat_file_id:
            # Запрос с использованием конкретного файла
            print(f"🔍 Отправляем запрос с файлом GigaChat: {gigachat_file_id}")
            
            result = giga_manager.ask_according_to_material(user_message, gigachat_file_id)
            
        else:
            # Общий запрос без привязки к файлу
            print("🔍 Отправляем общий запрос без файла")
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

        print(f"✅ Ответ получен за {processing_time:.2f} сек")

        response_data = {
            'response': ai_response,
            'status': 'success',
            'processing_time': f"{processing_time:.2f} сек",
            'used_file_id': file_id,
            'used_file_name': file_info['name'] if file_info else None
        }

        return jsonify(response_data)

    except Exception as e:
        print(f"❌ Ошибка при обработке запроса: {e}")
        return jsonify({
            'error': f'Внутренняя ошибка сервера: {str(e)}',
            'status': 'error'
        }), 500

@app.route('/api/files/<file_id>', methods=['DELETE'])
def delete_file(file_id):
    """Удаление файла и связанных данных"""
    try:
        # Получаем информацию о файле из базы
        file_info = get_file_from_database(file_id)
        if not file_info:
            return jsonify({'error': 'Файл не найден'}), 404
        
        gigachat_file_id = file_info.get('gigachat_file_id')
        file_name = file_info.get('name')
        
        # Удаляем файл из GigaChat
        if gigachat_file_id:
            try:
                giga_manager.delete_file_by_id(gigachat_file_id)
                print(f"🗑️ Файл удален из GigaChat: {gigachat_file_id}")
            except Exception as e:
                print(f"⚠️ Ошибка удаления из GigaChat: {e}")

        # Удаляем запись из базы данных
        delete_success = delete_file_from_database(file_id)
        
        if delete_success:
            return jsonify({
                'message': 'Файл успешно удален',
                'deleted_file_id': file_id,
                'deleted_file_name': file_name
            })
        else:
            return jsonify({'error': 'Не удалось удалить файл из базы данных'}), 500
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/files/clear', methods=['DELETE'])
def clear_all_files():
    """Удаление всех файлов"""
    try:
        # Получаем все файлы из базы
        all_files = get_all_files_from_database()
        
        # Удаляем все файлы из GigaChat
        giga_manager.delete_all_files()
        
        # Удаляем все записи из базы данных
        for file_info in all_files:
            delete_file_from_database(file_info['id'])
            print(f"🗑️ Удален файл из базы: {file_info['name']}")

        return jsonify({
            'message': f'Все файлы удалены ({len(all_files)} файлов)',
            'deleted_count': len(all_files)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/system/info', methods=['GET'])
def system_info():
    """Информация о системе"""
    try:
        # Информация о GigaChat
        gigachat_files = giga_manager.files
        
        # Информация о базе данных
        db_files = get_all_files_from_database()
        
        return jsonify({
            'gigachat': {
                'files_count': len(gigachat_files),
                'file_names': [file.fullname for file in gigachat_files],
                'file_ids': [file.id for file in gigachat_files]
            },
            'database': {
                'files_count': len(db_files),
                'file_names': [file['name'] for file in db_files],
                'total_size_mb': round(sum(file['file_size'] for file in db_files) / (1024 * 1024), 2)
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Запуск PDF Chat Server на http://localhost:5000")
    print("=" * 50)
    
    # Проверяем подключение к GigaChat
    try:
        files = giga_manager.files
        print(f"✅ Подключение к GigaChat успешно")
        print(f"📁 Доступно файлов в GigaChat: {len(files)}")
        for file in files:
            print(f"   - {file.fullname} (ID: {file.id})")
    except Exception as e:
        print(f"❌ Ошибка подключения к GigaChat: {e}")

    # Инициализируем Supabase
    supabase_initialized = init_supabase()
    if not supabase_initialized:
        print("❌ Не удалось подключиться к Supabase. Проверьте настройки.")
    
    print("=" * 50)
    print("📝 Доступные эндпоинты:")
    print("  GET  /api/health          - Проверка здоровья сервера")
    print("  POST /api/files/upload    - Загрузка PDF файла")
    print("  GET  /api/files           - Список файлов")
    print("  POST /api/chat            - Чат с AI")
    print("  DELETE /api/files/<id>    - Удаление файла")
    print("  DELETE /api/files/clear   - Очистка всех файлов")
    print("  GET  /api/system/info     - Информация о системе")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
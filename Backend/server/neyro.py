from pdf_segmenter import process_pdf, PDFSegmenter
from gigachat import GigaChat
from pathlib import Path

# Константы
DIRECTORY = Path("E:/Sber/Backend/server/")
API_TOKEN = 'MDE5OTc1YzktMTIxZS03NTM1LWEzNDYtNTUyY2Y4ZTMzYzg2OjcwYWJmNTM2LTI0YWEtNGJhMi05N2ZiLWU3YzQzNTVmYWEzYw=='
PDF_FILES = ["ТОМ_1.pdf", "ТОМ_2.pdf", "ТОМ_3.pdf", "ТОМ_4.pdf", "base.pdf"]


class File:
    """Класс для представления файла в системе GigaChat"""

    def __init__(self, index: int, id: str, fullname: str):
        self.index = index
        self.id = id
        self.fullname = fullname

    def __repr__(self):
        return f"File(index={self.index}, id='{self.id}', fullname='{self.fullname}')"


class GigaChatManager:
    """Менеджер для работы с GigaChat API"""

    def __init__(self, api_token: str):
        self.giga = GigaChat(
            credentials=api_token,
            verify_ssl_certs=False,
        )
        self._files_cache = None

    def _get_files_data(self):
        """Получение данных о файлах с кэшированием"""
        if self._files_cache is None:
            self._files_cache = self.giga.get_files()
        return self._files_cache

    @property
    def files(self) -> list[File]:
        """Список всех файлов в системе"""
        return [
            File(index, data.id_, data.filename)
            for index, data in enumerate(self._get_files_data().data)
        ]

    def delete_all_files(self):
        """Удаление всех файлов"""
        for file in self.files:
            self.giga.delete_file(file.id)
        self._files_cache = None  # Сброс кэша

    def delete_file_by_id(self, file_id: str):
        """Удаление файла по ID"""
        self.giga.delete_file(file_id)
        self._files_cache = None  # Сброс кэша

    def upload_file(self, file_path: str | Path):
        """Загрузка файла"""
        file_path = Path(file_path)
        with open(file_path, "rb") as file:
            self.giga.upload_file(file)
        self._files_cache = None  # Сброс кэша

    def get_files_in_dataset(self) -> list[str]:
        """Получение списка имен файлов в датасете"""
        return [file.fullname for file in self.files]

    # В файле neyro.py замените функцию ask_according_to_material:

    def ask_according_to_material(self, message: str, material_id: str = None):
        """Запрос на основе документа (исправленная версия)"""
        # Создаем промпт с указанием контекста документов
        prompt = f"""Ты - эксперт в области инженерии и машиностроения. 
Ты в полной мере владеешь материалом и терминами, ты не пользуешься условными обозначениями, 
а используешь в своей речи наименования материалов или инструментала, с которым работаешь.

Отвечай на основе загруженных в тебя технических документов.

Вопрос: {message}

Ответь технически грамотно:"""

        result = self.giga.chat({
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "attachments": ["620c1733-7d34-462d-8ff2-391a19cca465"],
                }
            ],
            "temperature": 0.1
        })
        return result


def process_pdf_files():
    """Обработка PDF файлов"""
    for filename in PDF_FILES:
        file_path = DIRECTORY / filename
        try:
            result_file = process_pdf(str(file_path))
            print(f"Файл успешно обработан: {result_file}")
        except Exception as e:
            print(f"Ошибка при обработке {filename}: {e}")
import pdfplumber
import pandas as pd
import sys
import time
from typing import Dict, List, Any

def print_progress(current: int, total: int, status: str = ""):
    """
    Выводит прогресс-бар в консоль
    
    Args:
        current (int): Текущий прогресс
        total (int): Общее количество
        status (str): Дополнительный статус
    """
    bar_length = 40
    progress = float(current) / float(total) if total > 0 else 0
    block = int(round(bar_length * progress))
    progress_bar = "[" + "=" * block + " " * (bar_length - block) + "]"
    
    percent = progress * 100
    text = f"\rОбработка: {progress_bar} {percent:.1f}% ({current}/{total}) {status}"
    
    sys.stdout.write(text)
    sys.stdout.flush()

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Извлекает весь текст из PDF файла с выводом прогресса
    
    Args:
        pdf_path (str): Путь к PDF файлу
        
    Returns:
        str: Извлеченный текст
    """
    full_text = ""
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"Начата обработка документа: {total_pages} страниц")
            
            for page_num, page in enumerate(pdf.pages, 1):
                # Обновляем прогресс
                print_progress(page_num, total_pages, f"Страница {page_num}: извлечение текста")
                
                # Извлекаем текст со страницы
                page_text = page.extract_text()
                if page_text:
                    full_text += f"--- Страница {page_num} ---\n{page_text}\n\n"
                
                # Небольшая задержка для визуализации прогресса
                time.sleep(0.1)
                    
            print(f"\n✅ Текст успешно извлечен со всех {total_pages} страниц")
            
    except Exception as e:
        raise Exception(f"Ошибка при извлечении текста: {str(e)}")
    
    return full_text

def extract_tables_from_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    Извлекает таблицы из PDF файла с выводом прогресса
    
    Args:
        pdf_path (str): Путь к PDF файлу
        
    Returns:
        dict: Словарь с таблицами в разных форматах
    """
    tables_data = {
        "tables_text": [],  # Таблицы в текстовом формате
        "tables_dataframes": [],  # Таблицы как DataFrame
        "tables_details": []  # Детальная информация о таблицах
    }
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            total_tables = 0
            
            print(f"\nНачато извлечение таблиц...")
            
            for page_num, page in enumerate(pdf.pages, 1):
                # Обновляем прогресс для страницы
                status = f"Страница {page_num}: поиск таблиц"
                print_progress(page_num, total_pages, status)
                
                # Извлекаем таблицы со страницы
                tables = page.extract_tables()
                page_tables_count = 0
                
                for table_num, table in enumerate(tables, 1):
                    if table and any(any(cell is not None and str(cell).strip() for cell in row) for row in table):
                        page_tables_count += 1
                        total_tables += 1
                        
                        # Сохраняем таблицу как текст
                        table_text = format_table_as_text(table, page_num, table_num)
                        tables_data["tables_text"].append(table_text)
                        
                        # Сохраняем таблицу как DataFrame
                        df = pd.DataFrame(table)
                        tables_data["tables_dataframes"].append({
                            "page": page_num,
                            "table_number": table_num,
                            "dataframe": df
                        })
                        
                        # Сохраняем детальную информацию
                        tables_data["tables_details"].append({
                            "page": page_num,
                            "table_number": table_num,
                            "rows": len(table),
                            "columns": len(table[0]) if table else 0
                        })
                
                # Выводим информацию о таблицах на текущей странице
                if page_tables_count > 0:
                    print(f"\r📊 Страница {page_num}: найдено {page_tables_count} таблиц" + " " * 50)
                else:
                    print(f"\r📄 Страница {page_num}: таблиц не найдено" + " " * 50)
                
                time.sleep(0.1)
            
            print(f"\n✅ Извлечение таблиц завершено. Всего найдено: {total_tables} таблиц")
            
    except Exception as e:
        raise Exception(f"Ошибка при извлечении таблиц: {str(e)}")
    
    return tables_data

def format_table_as_text(table: List[List[str]], page_num: int, table_num: int) -> str:
    """
    Форматирует таблицу в читаемый текстовый формат
    
    Args:
        table (list): Данные таблицы
        page_num (int): Номер страницы
        table_num (int): Номер таблицы
        
    Returns:
        str: Отформатированная таблица как текст
    """
    if not table:
        return ""
    
    # Фильтруем пустые строки
    filtered_table = []
    for row in table:
        if any(cell is not None and str(cell).strip() for cell in row):
            filtered_table.append([str(cell) if cell is not None else "" for cell in row])
    
    if not filtered_table:
        return ""
    
    # Определяем максимальную ширину для каждого столбца
    col_widths = []
    for col in range(len(filtered_table[0])):
        max_width = max(len(str(row[col])) if col < len(row) else 0 for row in filtered_table)
        col_widths.append(max_width + 2)  # Добавляем отступ
    
    # Создаем заголовок таблицы
    table_text = f"📋 Таблица {table_num} (Страница {page_num}):\n"
    
    # Добавляем разделитель
    separator = "+" + "+".join("-" * width for width in col_widths) + "+\n"
    table_text += separator
    
    # Добавляем строки таблицы
    for row in filtered_table:
        row_text = "|"
        for i, cell in enumerate(row):
            if i < len(col_widths):
                cell_content = str(cell) if cell is not None else ""
                row_text += f" {cell_content:<{col_widths[i]-2}} |"
        table_text += row_text + "\n"
        table_text += separator
    
    return table_text + "\n"

def combine_text_and_tables(text_content: str, tables_data: Dict[str, Any]) -> str:
    """
    Объединяет текст и таблицы в единый результат
    
    Args:
        text_content (str): Извлеченный текст
        tables_data (dict): Данные таблиц
        
    Returns:
        str: Объединенный результат
    """
    print("\n📝 Формирование итогового документа...")
    
    result = "=== ТЕКСТ ДОКУМЕНТА ===\n\n"
    result += text_content
    result += "\n\n=== ТАБЛИЦЫ ДОКУМЕНТА ===\n\n"
    
    # Добавляем все таблицы в текстовом формате
    for i, table_text in enumerate(tables_data["tables_text"], 1):
        result += table_text
        print_progress(i, len(tables_data["tables_text"]), f"Добавление таблиц")
        time.sleep(0.05)
    
    # Добавляем статистику
    result += f"\n=== СТАТИСТИКА ОБРАБОТКИ ===\n"
    result += f"Всего таблиц найдено: {len(tables_data['tables_text'])}\n"
    result += f"Всего страниц обработано: {len(set(detail['page'] for detail in tables_data['tables_details']))}\n"
    
    for detail in tables_data["tables_details"]:
        result += (f"Таблица {detail['table_number']} (стр. {detail['page']}): "
                  f"{detail['rows']} строк, {detail['columns']} столбцов\n")
    
    print(f"\n✅ Итоговый документ сформирован")
    
    return result

def process_pdf_to_txt(pdf_file_path: str) -> str:
    """
    Основная функция для обработки PDF файла и конвертации в TXT
    
    Args:
        pdf_file_path (str): Путь к PDF файлу для обработки
        
    Returns:
        str: Обработанный текст с сохранением таблиц и форматирования
        
    Raises:
        FileNotFoundError: Если файл не найден
        Exception: При ошибках обработки PDF
    """
    import os
    
    print("🚀 Запуск обработки PDF документа...")
    
    # Проверяем существование файла
    if not os.path.exists(pdf_file_path):
        raise FileNotFoundError(f"Файл не найден: {pdf_file_path}")
    
    # Проверяем расширение файла
    if not pdf_file_path.lower().endswith('.pdf'):
        raise ValueError("Файл должен быть в формате PDF")
    
    try:
        # Извлекаем текст
        text_content = extract_text_from_pdf(pdf_file_path)
        
        # Извлекаем таблицы
        tables_data = extract_tables_from_pdf(pdf_file_path)
        
        # Объединяем результаты
        final_result = combine_text_and_tables(text_content, tables_data)
        
        print(f"\n🎉 Обработка завершена успешно!")
        print(f"📊 Результат: {len(text_content)} символов текста, {len(tables_data['tables_text'])} таблиц")
        
        return final_result
        
    except Exception as e:
        print(f"\n❌ Ошибка при обработке PDF файла: {str(e)}")
        raise

def save_result_to_txt(result_text: str, output_path: str) -> None:
    """
    Сохраняет результат в TXT файл
    
    Args:
        result_text (str): Текст для сохранения
        output_path (str): Путь для сохранения файла
    """
    print(f"\n💾 Сохранение результата в файл: {output_path}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result_text)
    
    print(f"✅ Файл успешно сохранен: {output_path}")
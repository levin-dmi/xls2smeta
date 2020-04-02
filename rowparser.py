import re
from detector import detect


class RowParser:
    """
    Реализует логику построчной обработки входного файла КП
    """

    (START_CS, BEGIN_WAIT_CS, END_WAIT_CS) = range(3)
    (DETECTED_RT, NORMALIZED_RT, TRASH_RT, SYSTEM_RT) = range(4)

    def __init__(self):
        self.current_state = self.START_CS
        self.current_rows = []
        self.current_system = ''

        self.current_name = {}
        self.last_row_has_quantity = False
        self.last_row_perhaps_not_ended = False

    @staticmethod
    def to_float(num) -> float or None:
        """
        Пробуем преобразовать num (None, str, int, float) в число (float), если это возможно
        Если невозможно, возвращаем None
        """
        if not num:
            return 0.0
        elif type(num) == str:
            num.replace(' ', '').replace(',', '.')
            if num == '':
                return 0.0
        try:
            return float(num)
        except ValueError:
            return None

    @staticmethod
    def detect_trash(row: dict) -> bool:
        """
        Следующие строки признаются мусором:
        - все ячейки пустые
        - все ячейки содержат цифры
        - ячейка "количество" содержит текст
        """
        if not row['name'] and not row['brand'] and not row['code'] and not row['producer'] and \
                not row['unit'] and row['quantity'] == 0:  # Пустые строки
            return True
        elif type(row['name']) == int and type(row['brand']) == int and type(row['producer']) == int and \
                type(row['unit']) == int and type(row['quantity']) == float:  # Строки с цифрами
            return True
        elif row['quantity'] is None:  # Оставляем строки с цифрой или None в количстве
            return True
        return False

    @staticmethod
    def detect_system_name(row: dict) -> str or None:
        """
        Определяем, является ли строка началом новой системы
        Возвращаем имя системы или да
        """
        # Определяемые имена:
        system_names = (r'П[1-9]\d?В[1-9]\d?',  # П??В??
                        r'[ПВ][1-9]\d?.[ПВ][1-9]\d?р',  # П??/П??р В??/В??р
                        r'[ПВ][1-9]\d?р',  # П(В)??р
                        r'[ПВК][1-9]\d?',  # П(ВК)??
                        r'[ПВ]Д[1-9]\d?',  # П(В)Д??
                        r'ВЕ[1-9]\d?',)  # ВЕ??

        # Если это имя системы, то заполнена только ячейка 'name'
        if row['name'] != '' and row['brand'] == '' and row['code'] == '' and row['producer'] == '' and \
                row['unit'] == '' and row['quantity'] == 0.0:
            for sn in system_names:
                match = re.search(sn, row['name'])
                if match:
                    return match[0]
        return None

    def detect_new_name(self, test_name: str) -> bool:
        """
        Определяем, является ли test_name началом описания какой-либо номенклатуры
        """
        if 'ЗАЩИТА' in test_name and 'СТАТИЧ' in test_name:
            self.current_name = {'_material': 'ЗАЩИТА_СТАТИЧ'}
        elif 'МЕТАЛЛ ' in test_name:
            self.current_name = {'_material': 'МЕТАЛЛ'}
        elif 'ВОЗДУХОВОД' in test_name:
            self.current_name = {'_material': 'ВОЗДУХОВОД'}
        elif 'ЛЮЧОК ДЛЯ ЗАМЕРОВ ПАРАМЕТРОВ ВОЗДУХА' in test_name:
            self.current_name = {'_material': 'ЛЮЧОК'}
        else:
            return False
        return True

    def detect_standart_data(self, row: dict):
        """
        Собираем данные из всех столбцов кроме 'name'
        """
        unit_strs = {'КГ': 'кг', 'КОМП': 'компл', 'М2': 'м2', 'П.М': 'м', 'М': 'м', 'ШТ': 'шт', 'Т': 'т', }
        if row['brand']:
            self.current_name['brand'] = row['brand']
        elif 'brand' not in self.current_name:
            self.current_name['brand'] = ''
        if row['code']:
            self.current_name['code'] = row['code']
        elif 'code' not in self.current_name:
            self.current_name['code'] = ''
        if row['producer']:
            self.current_name['producer'] = row['producer']
        elif 'producer' not in self.current_name:
            self.current_name['producer'] = ''
        for un, norm_un in unit_strs.items():
            if un in row['unit']:
                self.current_name['unit'] = norm_un
                break
        if row['quantity'] > 0:
            self.current_name['quantity'] = row['quantity']

    def normalize_row(self, in_row: dict) -> dict:
        """
        Приводим строку в стандартный вид (убираем None, лишние пробелы и переводы строк, типы данных)
        """
        row: dict = in_row.copy()
        for cell_name, cell in row.items():
            if cell_name == 'quantity':  # Приводим количество к float если возможно, None меняем на 0.0
                row['quantity'] = self.to_float(row['quantity'])
                continue
            if not cell:
                cell = ''  # В остальных меняем None на ''
            if type(cell) != str:
                cell = str(cell)  # Приводим к строке
            row[cell_name] = ' '.join(cell.split())  # убираем лишние служебные символы
        return row

    @property
    def detect_new_block(self) -> bool:
        if self.detect_trash(self.current_rows[0]):
            return False
        if re.fullmatch(r'Ду', self.current_rows[0]['name'][0:2]):
            return False
        if re.fullmatch(r'[А-Я][а-я]', self.current_rows[0]['name'][0:2]):
            return True
        else:
            return False

    @property
    def detect_end_block(self) -> bool:
        if re.fullmatch(r'Ду', self.current_rows[-1]['name'][0:2]):
            return False
        if re.fullmatch(r'[А-Я]', self.current_rows[-1]['name'][0:1]):
            return True
        elif self.detect_trash(self.current_rows[-1]):
            return True
        else:
            return False

    def separate_trash_defect(self) -> dict:
        """
        Берем первую строку из стека, определяем строка мусорная или (в другом случае) ошибочная
        Формируем строку для возврата соответствующим образом
        """
        return_row = self.current_rows[0].copy()
        if self.detect_trash(self.current_rows[0]):
            return_row.update({'system': self.current_system, 'material': self.current_rows[0]['name'],
                               'dimension': '', 'type': self.TRASH_RT, 'incoming_rows': 1})
            return return_row
        else:
            mat_dim = detect(self.current_rows[0]['name'])
            return_row.update({'system': self.current_system, 'material': mat_dim['material'],
                               'dimension': mat_dim['dimension'], 'type': self.NORMALIZED_RT,
                               'incoming_rows': 1})
            return return_row

    def detect_string_not_block(self, row: dict) -> dict:
        """
        Определяем: строка мусорная или это имя системы или ошибочная строка
        Формируем строку для возврата соответствующим образом
        При необходимости меняем имя системы
        """
        return_row = row.copy()
        if self.detect_trash(row):  # Проверяем на мусор
            return_row.update({'system': self.current_system, 'material': row['name'],
                               'dimension': '', 'type': self.TRASH_RT, 'incoming_rows': 1})
            return return_row
        sn = self.detect_system_name(row)  # Проверяем на имя системы
        if sn:
            self.current_system = sn
            return_row.update({'system': self.current_system, 'material': row['name'],
                               'dimension': '', 'type': self.SYSTEM_RT, 'incoming_rows': 1})
            return return_row

        mat_dim = detect(row['name'])  # Иначе просто нормализуем
        return_row.update({'system': self.current_system, 'material': mat_dim['material'],
                           'dimension': mat_dim['dimension'], 'type': self.NORMALIZED_RT,
                           'incoming_rows': 1})
        return return_row

    def detect_first_row(self) -> dict:
        """
        Обрабатываем первую строку и возвращаем ee готовую к возврату
        кроме показателя 'incoming_rows'
        """
        mat_dim = detect(self.current_rows[0]['name'])
        detected = self.DETECTED_RT if mat_dim['detected'] else self.NORMALIZED_RT
        return_row = self.current_rows[0].copy()
        return_row.update({'system': self.current_system, 'material': mat_dim['material'],
                           'dimension': mat_dim['dimension'], 'type': detected, })
        return return_row

    def detect_row(self, row: dict, incoming_rows: int) -> dict:
        """
        Обрабатываем строку и возвращаем ee готовую к возврату в основную программу
        """
        mat_dim = detect(row['name'])
        detected = self.DETECTED_RT if mat_dim['detected'] else self.NORMALIZED_RT
        return_row = row.copy()
        return_row.update({'system': self.current_system, 'material': mat_dim['material'],
                           'dimension': mat_dim['dimension'], 'type': detected, 'incoming_rows': incoming_rows})
        return return_row

    def detect_block(self) -> list:
        """
        Формируем из блока строки на обработку, обрабатываем и возвращаем готовый список
        """
        # Определяем тип блока (строка, строка с добавкой, заголовок со строками или ошибочный)
        (STR_T, TWO_STR_T, HEADER_T, DEFECT_T) = range(4)
        block_type = DEFECT_T
        if len(self.current_rows) == 2 and self.current_rows[0]['quantity']:
            block_type = STR_T
        elif (len(self.current_rows) == 3 and self.current_rows[0]['quantity']
              and not self.current_rows[1]['quantity']):
            block_type = TWO_STR_T
        elif len(self.current_rows) > 2 and not self.current_rows[0]['quantity']:
            zero_num = False
            for row_index in range(0, len(self.current_rows) - 1):
                if self.current_rows[row_index]['quantity']:
                    zero_num = True
                elif zero_num:
                    break
            else:
                if zero_num:
                    block_type = HEADER_T

        if block_type == STR_T:  # Если блок - одна строка то просто ее обрабатываем
            return_row = self.detect_row(self.current_rows[0], 1)
            return [return_row, ]

        elif block_type == TWO_STR_T:  # Если блок две строки и в верхней количество то складываем в одну
            for col in self.current_rows[0]:
                if col != 'quantity':
                    self.current_rows[0][col] = self.current_rows[0][col] + ' ' + self.current_rows[1][col]
            return_row = self.detect_row(self.current_rows[0], 2)
            return [return_row, ]

        elif block_type == HEADER_T:  # Если блок 2+ и в верхней пусто
            header = self.current_rows[0]  # То во первых делаем из всех строк без количества header (объединяем)
            h_index = 0
            for h_index in range(1, len(self.current_rows) - 1):
                if not self.current_rows[h_index]['quantity']:
                    for col in header:
                        if col != 'quantity':
                            header[col] = header[col] + ' ' + self.current_rows[h_index][col]
                else:
                    break

            # Далее для каждой строки после хеадера делаем объединение хеадер плюс строка
            return_list = []
            for row_index in range(h_index, len(self.current_rows) - 1):
                for col in self.current_rows[row_index]:  # Объединяем
                    if col != 'quantity':
                        self.current_rows[row_index][col] = header[col] + ' ' + self.current_rows[row_index][col]
                incoming_rows = h_index + 1 if row_index == h_index else 1
                return_list.append(self.detect_row(self.current_rows[row_index], incoming_rows))
            return return_list

        else:  # Если структура блока ошибочна, то все обрабатываем как трэш/дефект
            return_list = []
            for row_index in range(0, len(self.current_rows) - 1):  # Все строки в трэш/ошибку
                return_list.append(self.detect_string_not_block(self.current_rows[row_index]))
            return return_list

    def parse(self, detect_row: dict) -> list:
        """
        Обрабатываем очередную строчку в виде словаря (типы значений любые, могут быть None):

        name - наименование и техническая характеристика
        brand - тип, марка
        code - код продукции
        producer - изготовитель, поставщик
        unit - единица измерения
        quantity - количество

        Возвращаем список строк (может быть пустым), количество зависит от того что мы распознавали.

        Возвращаемые строки (по умолчанию переменные str):
        system - имя системы
        material - материал
        dimension - параметры материала
        brand, code, producer - просто нормализуем
        unit - приводим к стандартным
        quantity - всегда float
        type - DETECTED_RT - распознан, NORMALIZED_RT - просто нормализован, TRASH_RT - мусор, SYSTEM_RT - имя системы
        incoming_rows - int - количество ранее полученных строк, вошедших в данный вывод
        """
        row = self.normalize_row(detect_row)
        self.current_rows.append(row)  # Записываем в стек

        if self.current_state == self.START_CS:  # ---- Если это самая первая строка
            self.current_state = self.BEGIN_WAIT_CS  # Ждем начала блока
            return []

        if self.current_state == self.BEGIN_WAIT_CS:  # ---- Если ждем начала блока
            if self.detect_new_block:  # - Если это новый блок
                self.current_state = self.END_WAIT_CS
            else:  # - Иначе это мусор или брак
                return_row: dict = self.detect_string_not_block(self.current_rows[0])  # Подготовить возврат
                self.current_rows.pop(0)  # Удаляем первую строку из стека
                return [return_row, ]

        if self.current_state == self.END_WAIT_CS:  # ---- Если ждем конца блока
            if self.detect_end_block:  # Проверяем последнюю строчку если конец то
                return_list: list = self.detect_block()  # Обработать блок
                while len(self.current_rows) > 1:  # Удалить блок, оставляем последнюю строку
                    self.current_rows.pop(0)
                    self.current_state = self.BEGIN_WAIT_CS
                return return_list
            else:  # Иначе продолжаем считывать блок
                return []

    def detect(self, detect_row: dict) -> dict or None:
        """
        Обрабатываем очередную строчку в виде словаря:

        name - наименование и техническая характеристика
        brand - тип, марка
        code - код продукции
        producer - изготовитель, поставщик
        unit - единица измерения
        quantity - количество

        Возвращаем None если ничего не определили, а если определили то изменяется:
        system - имя системы
        name - определенный материал
        data - параметры материала
        comment - комментарий к строке
        quantity - всегда float
        """
        row = detect_row.copy()

        # Приводим строку в стандартный вид (Капс, None, лишние пробелы и переводы строк, типы данных)
        for cell_name, cell in row.items():
            if cell_name == 'quantity':  # Приводим количество к float если возможно, None меняем на 0.0
                row['quantity'] = self.to_float(row['quantity'])
                continue
            cell = '' if not cell else cell  # В остальных меняем None на ''
            cell = str(cell) if type(cell) != str else cell  # Приводим к строке
            if cell_name == 'name' or cell_name == 'unit':  # Приводим параметр 'name' и 'unit 'к верхнему регистру
                row[cell_name] = cell.upper()
                continue
            row[cell_name] = ' '.join(cell.split())  # убираем лишние служебные символы

        # Если в предыдущей строке было количество а теперь нет, то старая система закончилась
        # Кроме случая двойной строки
        if not row['quantity'] and self.last_row_has_quantity and not self.last_row_perhaps_not_ended:
            self.last_row_has_quantity = False
            self.current_name.clear()

        # Определяем, не мусорная ли строка
        if self.detect_trash(row):
            self.current_name.clear()
            detect_row['comment'] = 'Мусор'
            return None

        # Проверяем строку на начало новой системы
        system_name = self.detect_system_name(row)
        if system_name:
            self.current_system = system_name
            self.current_name.clear()
            detect_row['comment'] = 'Новая система'
            detect_row['system'] = self.current_system
            return None

        # Проверяем не начался ли новый блок
        self.detect_new_name(row['name'])

        # Если не начался и до этого его не было - выходим
        if '_material' not in self.current_name:
            self.current_name.clear()
            return None

        # Собираем данные текущий строки в соответствии с текущим блоком
        # Вначале стандартные
        self.detect_standart_data(row)
        # Потом специальные
        if self.current_name['_material'] == 'ВОЗДУХОВОД':
            if 'ОЦИНК' in row['name']:  # Оцинкованный
                self.current_name['_type'] = 'ОЦИНКОВАННЫЙ'
            thick = re.search(r'[0-9][.,][0-9]', row['name'])  # Ищем толщину
            if thick:
                self.current_name['_thick'] = thick[0].replace('.', ',')
            s_size1 = re.search(r'[1-9][0-9]+[XХ×]', row['name'])  # Ищем размеры
            s_size2 = re.search(r'[XХ×][1-9][0-9]+', row['name'])
            if s_size1 and s_size2:
                self.current_name['data'] = s_size1[0][0:-1] + 'х' + s_size2[0][1:]
            else:
                r_size = re.findall(r'[1-9][0-9]{2,}', row['name'])
                if len(r_size) == 1:
                    self.current_name['data'] = r_size[0]

        if self.current_name['_material'] == 'ЗАЩИТА_СТАТИЧ':
            if 'СТАЛЬ' in row['name'] and 'ПОЛОС' in row['name']:  # Полоса стальная
                self.current_name['_type'] = 'ПОЛОСА_СТАЛЬНАЯ'
            thick = re.search(r'[0-9]+[XХ×]', row['name'])  # Ищем размеры
            size = re.search(r'[XХ×][1-9][0-9]+', row['name'])
            if thick and size:
                self.current_name['data'] = thick[0][0:-1] + 'х' + size[0][1:]

        if self.current_name['_material'] == 'МЕТАЛЛ':
            pass

        if self.current_name['_material'] == 'ЛЮЧОК':
            pass

        # Если есть количество и все обязательные данные для текущего блока собраны - формируем результат
        if 'quantity' in self.current_name:
            self.last_row_has_quantity = True
            if self.current_name['_material'] == 'ВОЗДУХОВОД':
                if '_type' in self.current_name and '_thick' in self.current_name and 'data' in self.current_name:
                    return_name = {'system': self.current_system, 'name': 'Воздуховод из оцинкованной стали',
                                   'data': self.current_name['_thick'] + 'х' + self.current_name['data'],
                                   'brand': self.current_name['brand'], 'code': self.current_name['code'],
                                   'producer': self.current_name['producer'], 'unit': self.current_name['unit'],
                                   'quantity': self.current_name['quantity']}
                    self.current_name.pop('data')

                    if self.last_row_perhaps_not_ended:  # Обрабока ситуации размещения информации на двух строчках
                        self.last_row_perhaps_not_ended = False  # с количеством в верхней
                        self.current_name.clear()
                    return return_name
                else:  # Количество есть а полей нет
                    # self.current_name.clear()
                    self.last_row_perhaps_not_ended = not self.last_row_perhaps_not_ended
                    return None
            elif self.current_name['_material'] == 'ЗАЩИТА_СТАТИЧ':
                if '_type' in self.current_name and 'data' in self.current_name:
                    return_name = {'system': self.current_system, 'name': 'Полоса стальная горячекатанная',
                                   'data': self.current_name['data'],
                                   'brand': self.current_name['brand'], 'code': self.current_name['code'],
                                   'producer': self.current_name['producer'], 'unit': self.current_name['unit'],
                                   'quantity': self.current_name['quantity']}
                    self.current_name.pop('data')

                    if self.last_row_perhaps_not_ended:  # Обрабока ситуации размещения информации на двух строчках
                        self.last_row_perhaps_not_ended = False  # с количеством в верхней
                        self.current_name.clear()
                    return return_name
                else:  # Количество есть а полей нет
                    # self.current_name.clear()
                    self.last_row_perhaps_not_ended = not self.last_row_perhaps_not_ended
                    return None
            elif self.current_name['_material'] == 'МЕТАЛЛ':
                return_name = {'system': self.current_system, 'name': 'Металл',
                               'data': '',
                               'brand': self.current_name['brand'], 'code': self.current_name['code'],
                               'producer': self.current_name['producer'], 'unit': self.current_name['unit'],
                               'quantity': self.current_name['quantity']}

                if self.last_row_perhaps_not_ended:  # Обрабока ситуации размещения информации на двух строчках
                    self.last_row_perhaps_not_ended = False  # с количеством в верхней
                    self.current_name.clear()
                return return_name

            elif self.current_name['_material'] == 'ЛЮЧОК':
                return_name = {'system': self.current_system, 'name': 'Металл',
                               'data': '',
                               'brand': self.current_name['brand'], 'code': self.current_name['code'],
                               'producer': self.current_name['producer'], 'unit': self.current_name['unit'],
                               'quantity': self.current_name['quantity']}

                if self.last_row_perhaps_not_ended:  # Обрабока ситуации размещения информации на двух строчках
                    self.last_row_perhaps_not_ended = False  # с количеством в верхней
                    self.current_name.clear()
                return return_name

            else:
                self.current_name.clear()
                return None



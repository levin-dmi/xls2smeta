import re
import configparser

"""
Здесь находится логика распознавания материалов
"""


def airthik_dim(name: str) -> str or None:
    """
    Ищем толщину воздуховода - число вида 0.2 или 1
    окружено пробелами или =1мм
    :param name: строка в которой ведем поиск
    :return: строку с толщиной или None если не нашли
    """
    name = name.upper()
    thick = re.search(r'[0-9][.,][0-9]', name)
    if thick:
        return thick[0].replace('.', ',')
    else:
        thick = re.search(r'[1-9]М', name)
        if thick:
            return thick[0][:-1]


def airduct_dim(name: str) -> str or None:
    name = name.upper()
    size = ''
    thick = airthik_dim(name)  # Ищем толщину
    if not thick:
        return None
    s_size1 = re.search(r'[1-9][0-9]+[XХ×]', name)  # Ищем размеры
    s_size2 = re.search(r'[XХ×][1-9][0-9]+', name)
    if s_size1 and s_size2:
        size = s_size1[0][0:-1] + 'х' + s_size2[0][1:]
    else:
        name = re.sub(r'\d{3,5}-\d{2}', '', name)  # Вырезаем ГОСТ
        r_size = re.findall(r'[1-9][0-9]{2,}', name)
        if len(r_size) == 1:
            size = r_size[0]
    if size:
        return thick + 'х' + size


def airconvert_dim(name: str) -> str or None:
    name = name.upper()
    thick = airthik_dim(name)  # Ищем толщину
    if not thick:
        thick = ''
    s_size = re.findall(r'[1-9][0-9]+[XХ×][1-9][0-9]+', name)  # Ищем размеры
    r_size = re.findall(r'Ø[1-9][0-9]+', name)
    if len(s_size) + len(r_size) == 2:
        size = thick + 'х' if thick else ''
        for s in s_size:
            size = size + '(' + re.sub(r'[XХ×]', 'х', s) + ')х'
        for s in r_size:
            size = size + '(' + re.sub(r'Ø', '', s) + ')х'
        return size[:-1]


def airtap_dim(name: str) -> str or None:
    name = name.upper()
    thick = airthik_dim(name)  # Ищем толщину
    if not thick:
        thick = ''
    angle = re.search(r'[1-9][0-9]+°', name)  # Ищем угол изгиба
    if angle:
        angle = angle[0].replace('.', ',')[:-1]
    else:
        return None
    s_size = re.findall(r'[1-9][0-9]+[XХ×][1-9][0-9]+', name)  # Ищем размеры
    r_size = re.findall(r'Ø[1-9][0-9]+', name)
    if len(s_size) + len(r_size) == 2:
        size = angle + '-' + thick + 'х' if thick else angle + '-'
        for s in s_size:
            size = size + '(' + re.sub(r'[XХ×]', 'х', s) + ')х'
        for s in r_size:
            size = size + '(' + re.sub(r'Ø', '', s) + ')х'
        return size[:-1]


def int_int_dim(name: str) -> str or None:
    name = name.upper()
    s_size1 = re.search(r'[1-9][0-9]*[XХ×]', name)  # Ищем размеры
    s_size2 = re.search(r'[XХ×][1-9][0-9]*', name)
    if s_size1 and s_size2:
        size = s_size1[0][0:-1] + 'х' + s_size2[0][1:]
        return size


def float_float_dim(name: str) -> str or None:
    name = name.upper()
    s_size1 = re.search(r'[1-9][0-9]*[.,]?[0-9]?[XХ×]', name)  # Ищем размеры
    s_size2 = re.search(r'[XХ×][1-9][0-9]*[.,]?[0-9]?', name)
    if s_size1 and s_size2:
        size = s_size1[0][0:-1] + 'х' + s_size2[0][1:]
        return size


def gost17375_dim(name: str) -> str or None:
    name = name.upper()
    size = re.search(r'[1-9][0-9]*-[^ ]*', name)  # Ищем размеры
    if size:
        size = re.sub(r'XХ×', 'х', size[0])
        return size


def gost17378_dim(name: str) -> str or None:
    name = name.upper()
    size = re.search(r'[КЭ]-[^ ]*', name)  # Ищем размеры
    if size:
        size = re.sub(r'XХ×', 'х', size[0])
        return size


def du_dim(name: str) -> str or None:
    name = name.upper()
    size = re.search(r'ДУ[0-9]+', name)  # Ищем размеры
    if size:
        return size[0][2:]


def int_dim(name: str) -> str or None:
    name = name.upper()
    size = re.search(r'[0-9]+', name)  # Ищем размеры
    if size:
        return size[0]


def pn_dim(name: str) -> str or None:
    name = name.upper()
    pn = re.search(r'PN[0-9]+', name)  # Ищем маркировку PN
    if not pn:
        return None

    r_size = re.findall(r'[Ø∅][1-9][0-9]+', name)  # Ищем размеры
    if r_size:
        return pn[0] + 'х' + r_size[0][1:]


def none_dim(name: str) -> str:
    return ' '


def detect(incoming_str: str) -> dict:
    """
    Детектирует во входящей строке стандартный материал и его типоразмеры
    Если не получилось то нормализует строку и пытается вытащить из нее размеры
    Возвращает словарь со строками 'material' и 'dimension'
    И признак 'detected' True/False
    """
    size_templates = (r'Ø\d{1,3}[0-9.,xх]+',  # Ø20
                      r'Ду[ =]?\d{1,3}',  # Ду 25
                      r'\d{2,4}[xх]\d-\d{2,4}[xх]\d',  # 123х6-321х2
                      r'\d{2,4}[xх][0-9.,]+-\d{2,4}[xх][0-9.,]+',  # 123x2,5-321x3.1
                      r'\d{2,4}[xх][0-9.,/]+',  # 123х2,5 123х3/4
                      r'.\d{3,4}.\d{3,4}...\d{3,4}.\d{3,4}.',
                      r' \d{3,4}[^ ]\d{3,4} ',)

    dim_functions = {'airduct': airduct_dim, 'int_int': int_int_dim, 'none': none_dim, 'airconvert': airconvert_dim,
                     'gost17375': gost17375_dim, 'float_float': float_float_dim, 'gost17378': gost17378_dim,
                     'airtap': airtap_dim, 'du': du_dim, 'int': int_dim, 'pn': pn_dim, }

    # читаем файл с определением материалов
    mat_config = configparser.ConfigParser(inline_comment_prefixes=('#',))
    mat_config.read('materials.conf')

    # Пробуем распознать материал
    for material in mat_config.sections():
        for key in mat_config[material]['keys'].split(','):
            if key not in incoming_str.upper():
                break
        else:  # Материал найден
            material_name = mat_config[material]['name']
            # Пробуем получить размеры
            dimension = dim_functions[mat_config[material]['dimension']](incoming_str)
            if dimension:  # Если размеры не получены то идем по пути нормализации
                result = {'material': material_name, 'dimension': dimension, 'detected': True}
                return result

    for st in size_templates:
        match = re.search(st, incoming_str)
        if match:
            material_name = re.sub(st, '', incoming_str)
            material_name = ' '.join(material_name.split())  # убираем лишние пробелы и служебные символы
            result = {'material': material_name, 'dimension': match[0], 'detected': False}
            return result
    return {'material': incoming_str, 'dimension': '', 'detected': False}

from collections import OrderedDict
from xml.etree import ElementTree
from html.parser import HTMLParser

SINGLE_TAGS = ['br','hr','img','input','param','meta','link']

def trans_value(value, ensure_number=True, ensure_boolean=True):
    if ensure_boolean is True:
        if value.lower() in ('true', 'on'):
            return True
        elif value.lower() in ('false', 'off'):
            return False
        elif value.lower() in ('null', 'none', '~'):
            return None

    if ensure_number is True:
        if value.isnumeric():
            return int(value)
        else:
            try:
                return float(value)
            except ValueError:
                pass
    return value

def trans_dict_value(data, ensure_number=True, ensure_boolean=True, ordered_dict=False):
    data = {key: trans_value(value, ensure_number, ensure_boolean) for key, value in data.items()}
    if ordered_dict is True:
        data = OrderedDict(data)
    return data


def get_xml_children(node):
    children = node.getchildren()
    if children:
        return [{'tag': node.tag,
                 'attrs': node.attrib,
                 'text': node.text.strip(),
                 'children': get_xml_children(child)
                 } for child in children]
    else:
        return {'tag': node.tag,
                'attrs': node.attrib,
                'text': node.text or None}


class MyHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.data = None

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in SINGLE_TAGS:
            return self.handle_startendtag(tag, attrs)
        self.stack.append(dict(tag=tag, attrs=dict(attrs), children=[], text=''))

    def handle_endtag(self, tag):
        self.data = current = self.stack.pop()
        if self.stack:
            parent = self.stack[-1]
            parent['children'].append(current)

    def handle_startendtag(self, tag, attrs):
        if self.stack:
            parent = self.stack[-1]
            parent['children'].append(dict(tag=tag, attrs=dict(attrs), children=[], text=''))

    def handle_data(self, data):
        if not data.strip():
            return
        if self.stack:
            self.stack[-1]['text'] = data.strip()


class Filez(object):
    def __init__(self):
        pass

    def open(self, file_path, **kwargs):
        encoding = kwargs.get('encoding', 'utf-8')
        with open(file_path, encoding=encoding) as f:
            raw = f.read()
        return raw

    def load_txt(self, file_path, **kwargs):
        encoding = kwargs.get('encoding', 'utf-8')
        with open(file_path, encoding=encoding) as f:
            data = [line.strip() for line in f.readlines()]
        return data

    def load_csv(self, file_path, **kwargs):
        csv = __import__('csv')
        encoding = kwargs.get('encoding', 'utf-8')
        header = kwargs.get('header', False)
        ensure_number = kwargs.get('ensure_number', True)
        ensure_boolean = kwargs.get('ensure_boolean', True)

        with open(file_path, encoding=encoding) as f:
            reader = csv.DictReader(f) if header else csv.reader(f)
            data = list(reader)

        if ensure_number or ensure_boolean:
            if header:
                collections = __import__('collections')
                data = list(map(lambda line:
                                collections.OrderedDict({key: trans_value(value, ensure_number, ensure_boolean)
                                                         for key,value in line.items()}), data))
            else:
                data = list(map(lambda line: list(map(lambda value: trans_value(value, ensure_number, ensure_boolean),
                                                      line)), data))
        return data

    def load_json(self, file_path, **kwargs):
        json = __import__('json')
        encoding = kwargs.get('encoding', 'utf-8')
        with open(file_path, encoding=encoding) as f:
            data = json.load(f)
        return data

    def load_yaml(self, file_path, **kwargs):
        yaml = __import__('yaml')
        encoding = kwargs.get('encoding', 'utf-8')
        with open(file_path, encoding=encoding) as f:
            data = yaml.safe_load(f)
        return data

    def load_config(self, file_path, **kwargs):  # todo case sensitive, sub section insure_boolean
        configparser = __import__('configparser')
        encoding = kwargs.get('encoding', 'utf-8')
        ensure_number = kwargs.get('ensure_number', True)
        ensure_boolean = kwargs.get('ensure_boolean', True)

        conf = configparser.ConfigParser()
        conf.read(file_path, encoding=encoding)

        if ensure_number or ensure_boolean:
            data = {section: trans_dict_value(dict(conf.items(section)), ensure_number, ensure_boolean, ordered_dict=True)
                    for section in conf.sections()}
        else:
            data = {section: dict(conf.items(section)) for section in conf.sections()}
        return data

    def load_excel(self, file_path, **kwargs):  # todo float->int ->str, FALSE -> False, '' -> None
        xlrd = __import__('xlrd')  # todo change to openpyxl
        header = kwargs.get('header', False)
        sheets = kwargs.get('sheets')
        wb = xlrd.open_workbook(file_path)
        all_sheets = wb.sheets()
        if not all_sheets:
            return
        def get_sh_data(sh, header):
            sh_data = [sh.row_values(i) for i in range(sh.nrows)]
            if header and sh_data:  # todo column name as header
                headers = sh_data[0]
                sh_data = [OrderedDict(zip(headers, line)) for line in sh_data[1:]]
            return sh_data

        if sheets:
            if isinstance(sheets, (list, tuple)):
                keep_sheets = [wb.sheet_by_index(i) if isinstance(i, int) else wb.sheet_by_name(i)
                               for i in sheets] # todo try
            elif sheets == 'all':
                keep_sheets = all_sheets
            else:
                return  # todo
            data = {}
            for sh in keep_sheets:
                data[sh.name] = get_sh_data(sh, header)
        else:
            sh = all_sheets[0]
            data = get_sh_data(sh, header)
        return data

    def load_xml(self, file_path, **kwargs):
        encoding = kwargs.get('encoding', 'utf-8')
        with open(file_path, encoding=encoding) as f:
            raw = f.read().strip()
        root = ElementTree.fromstring(raw)
        data = get_xml_children(root)
        return data

    def load_html(self, file_path, **kwargs):
        parser = MyHTMLParser()
        encoding = kwargs.get('encoding', 'utf-8')
        with open(file_path, encoding=encoding) as f:
            raw = f.read().strip()
        parser.feed(raw)
        return parser.data

    def load(self, file_path, **kwargs):  # todo file_type='config'
        if file_path.endswith('.csv'):
            return self.load_csv(file_path, **kwargs)
        elif file_path.endswith('.json'):
            return self.load_json(file_path, **kwargs)
        elif file_path.endswith('.yml') or file_path.endswith('.yaml'):
            return self.load_yaml(file_path, **kwargs)
        elif file_path.endswith('.conf') or file_path.endswith('.ini') or file_path.endswith('.config'):
            return self.load_config(file_path, **kwargs)
        elif file_path.endswith('.xls') or file_path.endswith('.xls'):
            return self.load_excel(file_path, **kwargs)
        elif file_path.endswith('.xml'):
            return self.load_xml(file_path, **kwargs)
        elif file_path.endswith('.html') or file_path.endswith('.htm'):
            return self.load_html(file_path, **kwargs)
        else:
            return self.load_txt(file_path, **kwargs)


file = Filez()


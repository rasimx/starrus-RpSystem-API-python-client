import logging
import requests
import random
import pprint
from django.core.mail import send_mail

import traceback

logger = logging.getLogger('starrus_api')

ERRORS_DICT = {
    1: "Неизвестная команда ФН",
    2: "Состояние ФН не соответствует присланной команде",
    3: "Ошибка ФН",
    4: "Ошибка контрольной суммы команды ФН",
    5: "Закончен срок эксплуатации ФН",
    6: "Архив ФН переполнен",
    7: "Дата и время не соответствую логике работы ФН",
    8: "Запрошенные данные отсутствуют в архиве ФН",
    9: "Некорректные параметры команды ФН",
    16: "Размер передаваемых данных превысил допустимый",
    17: "Нет транспортного соединения с ОФД",
    18: "Исчерпан ресурс криптографического сопроцессора ФН. Требуется закрыть фискальный режим",
    20: "Ресурс для хранения документов для ОФД исчерпан",
    21: "Исчерпан ресурс ожидания хранения данных в ФН",
    22: "Продолжительность смены долее 24 часов",
    23: "Неверная разница во времени между 2 операциями (более 5 минут)",
    32: "Сообщение от ОФД не может быть принято",
    40: "Ничего важного не изменилось, перерегистрация не нужна",
    41: "ИНН и регистрационный номер не должны меняться",
    51: "Параметр команды содержит неверные данные",
    52: "Отсутствуют данные для команды",
    55: "Команда не реализована",
    57: "Внутренняя ошибка устройство",
    60: "Смена открыта",
    61: "Смена не открыта",
    69: "Сумма всех оплат меньше итога чека",
    70: "Не хватает наличности в кассе",
    73: "Неверный тип документа для данной команды",
    74: "Чек открыт",
    77: "Сумма безналичных видов оплаты больше итога чека",
    79: "Неверный пароль для данной команды",
    80: "Данные печатаются",
    85: "Чек закрыт",
    90: "Скидка больше итога по строке",
    94: "Неверная команда",
    95: "Сторно больше итога чека",
    109: "Не хватает оборота по налогу",
    114: "Команда не допустима в этом подрежиме",
    115: "Команда не допустима в этом состоянии устройства",
    124: "Ошибочная дата",
    125: "Неверно сформированная дата",
    142: "Нулевой итог чека",
    192: "Ожидание подтверждения даты",
    196: "Номер смены в ФН не соответствует номеру смены в устройстве",
    200: "Тайм-аут принтера",
    207: "Неправильная дата/время",
    208: "Документ не содержит товарных позиций",
    238: "Номер группы, пришедший от сервера FCE не соответствует группе устройства",
    239: "Истёк срок аренды устройства",
    240: "Ошибка при выполнении комплексной команды (см. п. 2.4)",
    241: "Неизвестная команда в пакете",
    242: "Пустой запрос",
    243: "Отсутствует идентификатор запроса RequestId",
    244: "Ошибка при конвертации в JSON",
    245: "Отсутствует идентификатор пакетного запроса RequestId",
    246: "Ошибка при конвертации из JSON",
    247: "Несуществующая смена",
    248: "Изменены регистрационные параметры",
    249: "Ошибка транспортного уровня при получении данных из архива ФН",
    250: "Основная плата устройства не отвечает",
    252: "Неверная контрольная сумма файла",
    253: "Прочие ошибки принтера",
    254: "Принтер в оффлайне",
    255: "Фатальная ошибка устройства"
}

CASHBOX_STATES = {
    0: 'Состояние устройства после старта (фактически можно рассматривать это состояние как 4 «Смена закрыта»',
    2: 'Смена открыта',
    3: 'Смена открыта более 24 часов',
    4: 'Смена закрыта',
    6: 'Ожидает подтверждения даты',
    8: 'Открыт документ прихода',
    24: 'Открыт документ расхода',
    40: 'Открыт документ возврата прихода',
    56: 'Открыт документ возврата расхода',
    255: 'Фатальная ошибка устройства'
}

# ТИП ДОКУМЕНТА
DOC_TYPE_IN = 0
DOC_TYPE_RETURN = 1
DOC_TYPE_IN_RETURN = 2
DOC_TYPE_OUT_RETURN = 3

DOCUMENT_TYPES = (
    (DOC_TYPE_IN, "Приход"),
    (DOC_TYPE_RETURN, "Расход"),
    (DOC_TYPE_IN_RETURN, "Возврат прихода"),
    (DOC_TYPE_OUT_RETURN, "Возврат расхода"),
)

# ТИП ОПЛАТЫ
PAY_ATTRIBUTE_FFD_1_05 = 0
PAY_ATTRIBUTE_PREPAYMENT_FULL = 1
PAY_ATTRIBUTE_PREPAYMENT_PARTIAL = 2
PAY_ATTRIBUTE_ADVANCE = 3
PAY_ATTRIBUTE_FULL_PAYMENT = 4
PAY_ATTRIBUTE_PARTIAL_AND_CREDIT = 5
PAY_ATTRIBUTE_CREDIT = 6
PAY_ATTRIBUTE_CREDIT_PAYMENT = 7

PAY_ATTRIBUTES = (
    (PAY_ATTRIBUTE_FFD_1_05, "ФФД 1.05"),
    (PAY_ATTRIBUTE_PREPAYMENT_FULL, "Предоплата полная"),
    (PAY_ATTRIBUTE_PREPAYMENT_PARTIAL, "Предоплата частичная"),
    (PAY_ATTRIBUTE_ADVANCE, "Аванс"),
    (PAY_ATTRIBUTE_FULL_PAYMENT, "Полная оплата"),
    (PAY_ATTRIBUTE_PARTIAL_AND_CREDIT, "Частичный расчет и кредит"),
    (PAY_ATTRIBUTE_CREDIT, "Передача в кредит"),
    (PAY_ATTRIBUTE_CREDIT_PAYMENT, "Оплата кредита"),
)

# НДС
TAX_ID_18 = 1
TAX_ID_10 = 2
TAX_ID_0 = 3
TAX_ID_NONE = 4
TAX_ID_18_118 = 5
TAX_ID_10_100 = 6

TAX_ID_CODES = (
    (TAX_ID_18, "НДС 18%"),
    (TAX_ID_10, "НДС 10%"),
    (TAX_ID_0, "НДС 0%"),
    (TAX_ID_NONE, "Без налога"),
    (TAX_ID_18_118, "Ставка 18/118"),
    (TAX_ID_10_100, "Ставка 10/110"),
)

# НАЛОГОВЫЙ РЕЖИМ
TAX_MODE_OSN = 1
TAX_MODE_USN_D = 2
TAX_MODE_USN_D_R = 4
TAX_MODE_ENVD = 8
TAX_MODE_ESN = 16
TAX_MODE_PSN = 32

TAX_MODES = (
    (TAX_MODE_OSN, "ОСН"),
    (TAX_MODE_USN_D, "УСН Доход"),
    (TAX_MODE_USN_D_R, "УСН Доход-Расход"),
    (TAX_MODE_ENVD, "ЕНВД"),
    (TAX_MODE_ESN, "ЕСН"),
    (TAX_MODE_PSN, "ПСН"),
)

# МЕТОД РАСЧЕТА НАЛОГА
TAX_CALCULATION_METHOD_FROM_DEVICE = 0
TAX_CALCULATION_METHOD_AT_THE_END = 1
TAX_CALCULATION_METHOD_FOR_EACH_ITEM = 2

TAX_CALCULATION_METHODS = (
    (TAX_CALCULATION_METHOD_FROM_DEVICE, "Метод, установленный в таблице устройства №15"),
    (TAX_CALCULATION_METHOD_AT_THE_END, "Налоги считаются по итоговым данным документа"),
    (TAX_CALCULATION_METHOD_FOR_EACH_ITEM, "Налоги считаются от цены товарной позиции"),
)

# Признак предмета расчёта
OBJ_CALC = (
    (1, "о реализуемом товаре, за исключением подакцизного товара (наименование и иные сведения, описывающие товар)"),
    (2, "о реализуемом подакцизном товаре (наименование и иные сведения, описывающие товар)"),
    (3, "о выполняемой работе (наименование и иные сведения, описывающие работу)"),
    (4, "об оказываемой услуге (наименование и иные сведения, описывающие услугу)"),
    (5, "о приеме ставок при осуществлении деятельности по проведению азартных игр"),
    (6, "о выплате денежных средств в виде выигрыша при осуществлении деятельности по проведению азартных игр"),
    (7,
     "о приеме денежных средств при реализации лотерейных билетов, электронных лотерейных билетов, приеме лотерейных ставок при осуществлении деятельности по проведению лотерей"),
    (8, "о выплате денежных средств в виде выигрыша при осуществлении деятельности по проведению лотерей"),
    (
        9,
        "о предоставлении прав на использование результатов интеллектуальной деятельности или средств индивидуализации"),
    (10,
     "об авансе, задатке, предоплате, кредите, взносе в счет оплаты, пени, штрафе, вознаграждении, бонусе и ином аналогичном предмете расчета"),
    (11,
     "о вознаграждении пользователя, являющегося платежным агентом (субагентом), банковским платежным агентом (субагентом),комиссионером, поверенным или иным агентом"),
    (12, "о предмете расчета, состоящем из предметов, каждому из которых может быть присвоено значение от «1» до «11»"),
    (
    13, "о предмете расчета, не относящемуся к предметам расчета, которым может быть присвоено значение от «1» до «12»")
)

ACCESS_LEVELS = (
    (1, 'super_admin'),
    (2, 'admin'),
    (3, 'teller'),
)

COMMAND_ACCESS_RELATIONS = (
    ('GetFileHash', 1),
    ('SaveFile', 1),
    ('CheckFileSHA512', 1),
    ('SendMail', 1),
    ('PrintLog', 1),
    ('SetNetworkParameters', 1),
    ('Restart', 1),
    ('Reboot', 1),
    ('Poweroff', 1),
    ('PrepareTime', 1),
    ('PrepareDate', 1),
    ('ConfirmDate', 1),
    ('RegistrationReport', 1),
    ('ReRegistrationReportWithFNChange', 1),
    ('ReRegistrationReportWithoutFNChange', 1),
    ('GetRegistrationResult', 1),
    ('ClearDeviceData', 1),
    ('PrintRegistrationParameters', 1),
    ('StateReport', 1),
    ('GetLastFiscalDocumentInfo', 1),
    ('PrintLastFiscalDocument', 1),
    ('PrintFiscalDocumentByNumber', 1),
    ('GetFDOExchangeStatus', 1),
    ('GetFiscalDocumentByNumber', 1),
    ('GetShortFiscalDocumentByNumber', 1),
    ('GetFDOTicket', 1),
    ('SetTableField', 1),
    ('GetTableField', 1),
    ('CloseFiscalMode', 1),
    ('MakeCorrectionDocument', 1),
    ('PrintSavedDocuments', 1),
    ('CloseTurn', 2),
    ('IntermediateTurnReport', 2),
    ('Complex', 3),
    ('OpenTurn', 3),
    ('AddLineToDocument', 3),
    ('LongDeviceStatus', 3),
    ('PrintString', 3),
    ('GetMoneyRegister', 3),
    ('CutPaper', 3),
    ('FeedPaper', 3),
    ('CloseDocument', 3),
    ('CancelDocument', 3),
    ('GetSubtotal', 3),
    ('PrintLastSavedDocument', 3),
    ('OpenDocument', 3),
    ('AddPhoneOfTransferOperator', 3),
    ('AddCGN', 3),
    ('CashDrawerStatus', 3),
    ('CashDrawer', 3),
    ('AddPhoneOrEmailOfCustomer', 3),
    ('NoOperation', 3),
)

DEVICE_STATE_AFTER_START = 0
DEVICE_STATE_TURN_OPEN = 2
DEVICE_STATE_TURN_OPEN_MORE_24 = 3
DEVICE_STATE_TURN_CLOSED = 4
DEVICE_STATE_AWAIT_COMFIRM_DATE = 6
DEVICE_STATE_OPEN_DOC_IN = 8
DEVICE_STATE_OPEN_DOC_OUT = 24
DEVICE_STATE_OPEN_DOC_IN_RETURN = 40
DEVICE_STATE_OPEN_DOC_OUT_RETURN = 56
DEVICE_STATE_FAIL = 255


class BatchApi:
    def __init__(self, api_url, superadmin_password, admin_password, cashier_password):
        self.api_url = api_url
        self.superadmin_password = superadmin_password
        self.admin_password = admin_password
        self.cashier_password = cashier_password
        self.requests = []
    
    def _request(self, req_name, request_data=None):
        url = "{url}/fr/api/v2/{req_name}".format(url=self.api_url, req_name=req_name)
        
        if 'RequestId' not in request_data:
            request_data["RequestId"] = str(random.uniform(0, 20))
        
        try:
            response = requests.post(url, json=request_data, timeout=30)
        except requests.exceptions.RequestException as e:  # This is the correct syntax
            logger.error(traceback.format_stack())
            logger.error(traceback.format_exc())
            raise
        else:
            return response.json()
    
    def _get_errors(self, resp, request_data):
        if 'Error' in resp and resp['Error']:
            msgs = []
            error_number = resp['Error']
            msgs.append('{}: {}'.format(str(error_number), ERRORS_DICT[error_number]))
            
            if 'ErrorMessages' in resp:
                msgs.append('\n'.join(resp['ErrorMessages']))
            
            for operation in resp['Responses']:
                req_type = operation['Path'].replace('/fr/api/v2/', '')
                if 'Response' in operation:
                    if operation['Response'].get('Error'):
                        number = resp['Error']
                        msgs.append('\n{} - {}: {}'.format(req_type, str(number), ERRORS_DICT[number]))
            
            logger.error('request_data: ' + str(request_data))
            logger.error("Starrus Error %s: (%s)", error_number, msgs)
            
            # elif 'Response' in resp and resp['Response']['Error'] != 0:
            #     resp_response = resp['Response']
            #     error_number = str(resp_response['Error'])
            #     error_messages = error_number + ': ' + ERRORS_DICT[str(resp_response['Error'])]
            #     if 'ErrorMessages' in resp_response:
            #         error_messages = '\n'.join(resp_response['ErrorMessages'])
            #     logger.error('request_data: ' + str(request_data))
            #     logger.error("Starrus Error %s: (%s)", error_number, error_messages)
            #     raise Exception(error_messages)
            
            return '\n'.join(msgs)
        
        return None
    
    def apply(self):
        request_name = 'Batch'
        
        request_data = {
            "ShortResponse": False,
            "Requests": self.requests
        }
        self.requests = []
        resp = self._request(request_name, request_data)
        
        errors = self._get_errors(resp, request_data)
        if errors:
            raise Exception(errors)
        
        else:
            responses = {}
            
            for item in resp['Responses']:
                path = item['Path'].replace('/fr/api/v2/', '')
                response = item['Response'] if 'Response' in item else None
                responses[path] = response
            
            self.requests = []
            return responses
    
    def _add_operation(self, req_name, params=None):
        request = {
            "Path": "/fr/api/v2/{}".format(req_name),
            "ContinueWhenTransportError": False,
            "ContinueWhenDeviceError": False,
        }
        
        if params:
            request.update(params)
        
        if "Request" not in request:
            request["Request"] = {}
        
        # get_password
        access_relations_dict = dict(ACCESS_LEVELS)
        command_access_relations_dict = dict(COMMAND_ACCESS_RELATIONS)
        access_level = access_relations_dict[command_access_relations_dict[req_name]]
        password = int(getattr(self, access_level + '_password'))
        
        request["Request"]["Password"] = password
        
        self.requests.append(request)
    
    def open_turn(self, force=False):
        params = {}
        if not force:
            params["SkipWhenModeNotIn"] = [
                DEVICE_STATE_AFTER_START,
                DEVICE_STATE_TURN_CLOSED
            ]
        
        self._add_operation('OpenTurn', params)
    
    def close_turn(self, force=False):
        params = {}
        if not force:
            params["SkipWhenTrue"] = "(or (= device-mode DM-TURN-CLOSE) " \
                                     "(not (or (> sec-since-turn-open 86000) (>= docs-in-turn 8000))))"
        
        self._add_operation('CloseTurn', params)
    
    def cancel_document(self, force=False):
        params = {
            "Request": {
                "DocumentType": DOC_TYPE_IN,
            }
        }
        if not force:
            params["SkipWhenModeNotIn"] = [
                DEVICE_STATE_OPEN_DOC_IN,
                DEVICE_STATE_OPEN_DOC_OUT,
                DEVICE_STATE_OPEN_DOC_IN_RETURN,
                DEVICE_STATE_OPEN_DOC_OUT_RETURN
            ]
        
        self._add_operation('CancelDocument', params)
    
    def open_document(self, doc_type):
        params = {
            "Request": {
                "DocumentType": doc_type,
            }
        }
        
        self._add_operation('OpenDocument', params)
    
    def close_document(self, cash, noncash):
        params = {
            "Request": {
                "Cash": int(float(cash) * 100),  # сумма оплаты наличными в копейках
                # "NonCash": [int(), int(noncash) * 100, int()],  # оплата безналичными,
                "NonCash": [int(float(noncash) * 100)],  # оплата безналичными,
                "AdvancePayment": int(),  # Сумма оплаты предоплатой (зачётом аванса)
                "Credit": int(),  # Сумма оплаты постоплатой (в кредит)
                "Consideration": int(),  # Сумма оплаты встречным предоставлением
                # "TaxMode": TAX_MODE_USN_D,  # Применяемая в чеке система налогообложения, Упрощённая доход(1) необходимо указать, если при регистрации было задано более одной системы>
                "NoFetch": False,
                "NoRender": False,
                "PaymentAgentModes": 0,
                # "Place": "",  # Место расчетов. Значение по умолчанию из регистрационных данных
                "TaxCalculationMethod": TAX_CALCULATION_METHOD_AT_THE_END,  # Метод расчета налогов в чеке
                
            }
        }
        
        self._add_operation('CloseDocument', params)
    
    def no_operation(self):
        self._add_operation('NoOperation')
    
    def add_line_to_document(self, doc_type, name, qty, price):
        params = {
            "Request": {
                # "DocumentType": DOC_TYPE_IN,
                "DocumentType": doc_type,
                "Qty": int(qty) * 1000,  # Количество в тысячных долях,
                "Price": int(float(price) * 100),  # цена в копейках
                # "SubTotal": int(1000),  # итог по строке
                "PayAttribute": PAY_ATTRIBUTE_FULL_PAYMENT,  # Признак способа расчёта (таб. 9)
                # "LineAttribute": 3,
                "TaxId": TAX_ID_NONE,  # код налога, в моем случае - без налога(4)
                "Description": name
            }
        }
        
        self._add_operation('AddLineToDocument', params)
    
    def add_phone_or_email_of_customer(self, phone_or_email):
        params = {
            "Request": {
                "Value": phone_or_email,
            }
        }
        self._add_operation('AddPhoneOrEmailOfCustomer', params)
    
    def get_short_fiscal_document_by_number(self, fiscal_doc_number):
        params = {
            "Request": {
                "FiscalDocNumber": int(fiscal_doc_number)
            }
        }
        
        self._add_operation('GetShortFiscalDocumentByNumber', params)
    
    def get_fdo_exchange_status(self):
        self._add_operation('GetFDOExchangeStatus')
    
    def get_last_fiscal_document_info(self):
        self._add_operation('GetLastFiscalDocumentInfo')
    
    def long_device_status(self):
        self._add_operation('LongDeviceStatus')

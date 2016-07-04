# coding: utf8

import os
import json
import datetime
import time
import MySQLdb
from flask import render_template, request, redirect, url_for, Flask, session, Response, abort, flash, Session
from flask_login import LoginManager, login_user, logout_user, current_user, login_required

SQL_HOST = 'localhost'
SQL_USER = 'root'
SQL_PASSWD = '1234'
SQL_DB_NAME = 'taskadmin'
USER_DB_FILENAME = 'user_db1'
DATABASE_FILE_NAME = '/home/lax/PycharmProjects/learn1/database5'
ADD_DATABASE_FILE_NAME = '/home/lax/PycharmProjects/learn1/add_database5'
DATETIME_FORMAT = '%d/%m/%Y %H:%M:%S'
EVENT_TYPES = {1: 'Тривога', 2: 'Несправність', 3: 'Заява ВО', 4: 'Внутрішнє завдання', 5: 'Інше'}
STATUS_TYPES = {1: 'Виконано: ', 2: 'Очікується підтвердження', 3: 'Контроль до: ', 4: 'Очікуються дії ВО',
                5: 'Активний'}
ACTION_TYPES = {1: 'Створено завдання, виконавець:', 2: 'Повторна подія', 3: 'Додаткова інформація',
                4: 'Зміна виконавця на:', 5: 'Виконання', 6: 'Відтермінування до:', 7: 'Очікування на дії ВО',
                8: 'Запит на закриття завдання', 9: 'Закриття завдання', 10: 'Повторне відкриття завдання',
                11: 'Замінено обладнання', 12: 'Встановлено підмінне обладнання'}


app = Flask(__name__)
app.secret_key = 'vfjvjdfFVFDFDVdvf_)vfvx45127%vdkkmkkllewrwasvxv'


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

sql_database = MySQLdb.connect(host=SQL_HOST, user=SQL_USER, passwd=SQL_PASSWD, charset='utf8', db=SQL_DB_NAME)

##################################################################################################################


class UserManager(object):
    def __init__(self, db_file_name):
        """db structure
        {'abc..(username)': {'passwd'(password for login): 'qwerty...'
                             'acc_level(access level)': 0(admin)
                             }"""
        self.db_file_name = db_file_name
        if os.path.isfile(self.db_file_name):  # Check if additional database exists
            with open(self.db_file_name, 'r') as user_database_file:
                self.user_database = user_database_file.read().strip()
                self.user_database = json.loads(self.user_database)
        else:
            with open(self.db_file_name, 'w') as user_database_file:
                self.user_database = {}
                user_database_file.write(json.dumps(self.user_database))

    def get_userid(self, username):
        if username in self.user_database:
            return username + '_uid'.decode()
        else:
            return None

    def get_username(self, uid):  # Edited, not finished !!!!!!
        # name = uid.encode().split('_')[0]
        # if name in self.user_database:
        #    return 'admin'
        # else:
        return 'admin'

    def get_access_level(self, uid):
        name = uid.encode().split('_')[0]
        if name in self.user_database:
            return self.user_database[name]['acc_level']
        else:
            return None

    def check_login(self, name, password):
        if name in self.user_database:
            if password == self.user_database[name]['passwd']:
                return True
            else:
                return False
        else:
            return False

    def get_user(self, name=None, uid=None):
        if not name is None:
            user_inst = User(name + '_uid'.decode(), name, self.user_database[name]['acc_level'])
        elif not uid is None:
            name = uid.encode().split('_')[0]
            user_inst = User(uid, name, self.user_database[name]['acc_level'])
        else:
            user_inst = None
        return user_inst

    def new_user(self, name, password, acc_level):
        self.user_database[name] = {'passwd': password,
                                    'acc_level': acc_level
                                    }
        with open(self.db_file_name, 'w') as user_database_file:
            user_database_file.write(json.dumps(self.user_database))


class User(object):
    def __init__(self, uid, name, rights):
        self.id = uid
        self.name = name
        self.rights = rights
        self.data_container = {}

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id.decode()


def get_user_rights():
    if hasattr(current_user, 'rights'):
        return current_user.rights
    else:
        return None


def store_user_data(data):
    if hasattr(current_user, 'data_container'):
        current_user.data_container = data


def get_user_data():
    if hasattr(current_user, 'data_container'):
        return current_user.data_container
    else:
        return None


@login_manager.user_loader
def load_user(uid):
    return user_manager.get_user(uid=uid)

#################################################################################################################


class SysinfoDatabase(object):
    """ Current database structure
    {timestamp (in seconds):  {
                               'cpu_user': 45.33,
                               'cpu_sys': 17.22,
                               'cpu_total': 60.11,
                               ...
                               'hdd_free':5952
                               }
    } """

    def __init__(self, db_file_name, datetime_format):
        self.db_file_name = db_file_name
        self.datetime_format = datetime_format
        if not os.path.isfile(self.db_file_name):
            self.sysinfo_database = {}
            with open(self.db_file_name, 'w') as self.database_file:
                self.database_file.write(json.dumps(self.sysinfo_database))
        else:
            with open(self.db_file_name, 'r') as self.database_file:
                self.sysinfo_database = self.database_file.read().strip()
                self.sysinfo_database = json.loads(self.sysinfo_database)

        self.db_index_timestamps = self.sysinfo_database.keys()
        self.db_index_timestamps.sort(reverse=True)
        self.sysinfo_keywords = ['cpu_user', 'cpu_sys', 'cpu_total', 'cpu_idle', 'mem_total', 'mem_used',
                                 'mem_free', 'mem_cached', 'hdd_total', 'hdd_used', 'hdd_free']

    def get_last_record_hour(self):  # Returns hour of last record in database
        return datetime.datetime.fromtimestamp(float(self.db_index_timestamps[0])).hour

    def select(self, start=None, end=None, hour_periods_limit=12):  # Select from database
        select_result = {}
        if not self.sysinfo_database:
            return select_result
        if start is None:
            start = self.db_index_timestamps[0]
        else:
            start = str(time.mktime(datetime.datetime.strptime(start, self.datetime_format).timetuple()))
        if end is None:
            end = self.db_index_timestamps[len(self.db_index_timestamps) - 1]
        else:
            end = str(time.mktime(datetime.datetime.strptime(end, self.datetime_format).timetuple()))
        if hour_periods_limit < 0:
            hour_periods_limit = 12

        current_period_timestamp = []
        periods_in_select_result = 0

        for index_timestamp in self.db_index_timestamps:
            if start >= index_timestamp >= end:
                index_timestamp_asobject = datetime.datetime.fromtimestamp(float(index_timestamp))
                if current_period_timestamp != index_timestamp_asobject.strftime('%Y,%m,%d,%H'):
                    current_period_timestamp = index_timestamp_asobject.strftime('%Y,%m,%d,%H')
                    periods_in_select_result += 1
                select_result[index_timestamp_asobject] = self.sysinfo_database[index_timestamp]
            if periods_in_select_result >= hour_periods_limit:
                break
            else:
                if index_timestamp < end:
                    break
        return select_result

    def average(self, input_data, groupbyhour=True):
        input_data_timestamps = input_data.keys()
        input_data_timestamps.sort(reverse=True)

        avg_period_result = {'cpu_user': 0, 'cpu_sys': 0, 'cpu_total': 0, 'cpu_idle': 0,
                             'mem_total': 0, 'mem_used': 0, 'mem_free': 0, 'mem_cached': 0,
                             'hdd_total': 0, 'hdd_used': 0, 'hdd_free': 0
                             }
        average_result = {}
        periods_in_result = 0
        averaged_in_period = 0
        period_timestamp = None

        for in_data_timestamp in input_data_timestamps:
            if not period_timestamp:
                period_timestamp = in_data_timestamp.strftime('%Y,%m,%d,%H')

            if groupbyhour:
                if period_timestamp != in_data_timestamp.strftime('%Y,%m,%d,%H'):
                    for key in self.sysinfo_keywords:
                        avg_period_result[key] /= averaged_in_period
                    average_result[datetime.datetime.strptime(period_timestamp, '%Y,%m,%d,%H')] = avg_period_result
                    periods_in_result += 1
                    averaged_in_period = 0
                    avg_period_result = {'cpu_user': 0, 'cpu_sys': 0, 'cpu_total': 0, 'cpu_idle': 0,
                                         'mem_total': 0, 'mem_used': 0, 'mem_free': 0, 'mem_cached': 0,
                                         'hdd_total': 0, 'hdd_used': 0, 'hdd_free': 0
                                         }
                    period_timestamp = in_data_timestamp.strftime('%Y,%m,%d,%H')
            single_db_record = input_data[in_data_timestamp]
            for key in self.sysinfo_keywords:
                avg_period_result[key] += single_db_record[key]
            averaged_in_period += 1

        if averaged_in_period != 0:
            for key in self.sysinfo_keywords:
                avg_period_result[key] /= averaged_in_period
                average_result[datetime.datetime.strptime(period_timestamp, '%Y,%m,%d,%H')] = avg_period_result
            periods_in_result += 1
        return average_result, periods_in_result

    def new_record(self, timestamp, data):  # Adding new record into database
        self.sysinfo_database[time.mktime(timestamp.timetuple())] = data
        with open(self.db_file_name, 'w') as self.database_file:
            self.database_file.write(json.dumps(self.sysinfo_database))
        self.db_index_timestamps = self.sysinfo_database.keys()
        self.db_index_timestamps.sort(reverse=True)

    def erase(self):  # Database full erase
        self.sysinfo_database = {}
        with open(self.db_file_name, 'w') as self.database_file:
            self.database_file.write(json.dumps(self.sysinfo_database))

    def clean(self, size_limit=500):  # Cleans database from old records (default is 500 record limit)
        database_size = len(self.db_index_timestamps)
        while database_size > size_limit:
            del self.sysinfo_database[self.db_index_timestamps[database_size - 1]]
            database_size -= 1
        with open(self.db_file_name, 'w') as self.database_file:
            self.database_file.write(json.dumps(self.sysinfo_database))
        self.db_index_timestamps = self.sysinfo_database.keys()
        self.db_index_timestamps.sort(reverse=True)


def extend_html_table(e_html_table, data, timestamp):
    e_html_table += """
                <tr>
                    <td>Averaging period {11} {12}:00 - {12}:59</td>
                </tr>
                <tr>
                    <td>CPU</td>
                    <td>total:{0:.2f}</td>
                    <td>user:{1:.2f}</td>
                    <td>system:{2:.2f}</td>
                    <td>idle:{3:.2f}</td>
                </tr>
                <tr>
                    <td>Memory</td>
                    <td>total:{4:d}</td>
                    <td>used:{5:d}</td>
                    <td>free:{6:d}</td>
                    <td>cached:{7:d}</td>
                </tr>
                <tr>
                    <td>Hard disk drive</td>
                    <td>total:{8:d}</td>
                    <td>used:{9:d}</td>
                    <td>free:{10:d}</td>
                </tr>
    """.format(data['cpu_total'], data['cpu_user'], data['cpu_sys'],
               data['cpu_idle'], data['mem_total'], data['mem_used'],
               data['mem_free'], data['mem_cached'], data['hdd_total'],
               data['hdd_used'], data['hdd_free'], timestamp.date(),
               timestamp.hour)

    return e_html_table

#################################################################################################################


class TaskAdmin(object):
    def __init__(self, sql_db_object):
        self.sql_database = sql_db_object
        self.sql_cursor = self.sql_database.cursor()

    def new_task(self, data):
        """
        :param objectid: object id in separate object db
        :param creator: id of person who created task in separate user db
        :param eventtype: type of event (alarm-1, malfunction-2, client request-3, inner task-4, other-5)
        :param event: text description of the event
        :param eventdate: when event happened (accepts datetime object)
        :param assignedto: id of person who is assigned to do the task in separate user db
        :param status: status (closed-1, waiting to confirm-2, pending to-3, wait for action-4, active-5)
        :param priority: priority of task (low-1, normal-2, high-3, critical-4)
        :return:
        """
        if len(data['event']) > 199:
            data['event'] = data['event'][0:190] + ' ...'  # Limit event preview text size
        data['eventdate'] = data['eventdate'].strftime('%Y-%m-%d %H:%M:%S')
        if data['pendclosedate'] is not None:
            data['pendclosedate'] = data['pendclosedate'].strftime('%Y-%m-%d %H:%M:%S')
        self.sql_cursor.execute('INSERT INTO tasklist (objectid, creator, eventtype, event, eventdate, assignedto, '
                                'status, priority, pendclosedate) VALUES ({0:d}, {1:d}, {2:d}, "{3:s}", "{4:s}", '
                                '{5:d}, {6:d}, {7:d}, "{8:s}")'
                                .format(data['objectid'], data['creator'], data['eventtype'], data['event'],
                                        data['eventdate'], data['assignedto'], data['status'], data['priority'],
                                        data['pendclosedate']))
        self.sql_database.commit()

    def new_action(self, action_type, action, reasign_to=None, pendclose_date=None):
        pass



    def get_active_tasks(self):
        self.sql_cursor.execute('SELECT id, tstamp, objectid, creator, eventtype, event, eventdate, assignedto, status,'
                                ' priority, pendclosedate FROM tasklist ORDER by priority DESC LIMIT 100')
        return self.sql_cursor.fetchall()

    def get_task_details(self, taskid):
        self.sql_cursor.execute('SELECT id, tstamp, objectid, creator, eventtype, event, eventdate, assignedto, status,'
                                ' priority, pendclosedate FROM tasklist WHERE id=%d' % taskid)
        task_info = self.sql_cursor.fetchall()
        self.sql_cursor.execute('SELECT tstamp, actionby, actiontype, action, assignedto, pendclosedate FROM'
                                ' actionslist WHERE id=%d ORDER BY id ASC' % taskid)
        actions = self.sql_cursor.fetchall()
        return task_info, actions

    def prepare_data(self, data):
        task_details = {}
        for index, task_data in enumerate(data):
            object_data = object_manager.search_objects(task_data[2], search_by='id')
            object_data = object_manager.prepare_data(object_data)[0]
            task_details[index] = {}
            task_details[index]['id'] = task_data[0]
            task_details[index]['last_act_time'] = change_datetime_format(task_data[1], DATETIME_FORMAT, 'datetime')
            task_details[index]['object_number'] = object_data['number']
            task_details[index]['object_name'] = object_data['name']
            task_details[index]['object_address'] = object_data['address']
            task_details[index]['creator'] = user_manager.get_username(task_data[3]).decode('utf-8')
            task_details[index]['event_type'] = EVENT_TYPES[task_data[4]].decode('utf-8')
            task_details[index]['event'] = task_data[5]
            task_details[index]['event_date'] = change_datetime_format(task_data[6], DATETIME_FORMAT, 'date')
            task_details[index]['event_time'] = change_datetime_format(task_data[6], DATETIME_FORMAT, 'time')
            task_details[index]['assigned_to'] = user_manager.get_username(task_data[7]).decode('utf-8')
            task_details[index]['status'] = STATUS_TYPES[task_data[8]].decode('utf-8')
            if task_data[8] == 1 or task_data[8] == 3:
                task_details[index]['status_datetime'] = change_datetime_format(task_data[10],
                                                                                DATETIME_FORMAT, 'datetime')
            else:
                task_details[index]['status_datetime'] = ''
            task_details[index]['priority_num'] = task_data[9]
        return task_details

    def setup_database(self):
        self.sql_cursor.execute('CREATE TABLE tasklist (id INT NOT NULL PRIMARY KEY AUTO_INCREMENT, tstamp TIMESTAMP, '
                                'objectid INT, FOREIGN KEY (objectid) REFERENCES objectlist(id), creator SMALLINT, '
                                'eventtype TINYINT, event VARCHAR(200), '
                                'eventdate DATETIME, assignedto SMALLINT, status TINYINT, '
                                'priority TINYINT, pendclosedate DATETIME)')

        self.sql_cursor.execute('CREATE TABLE actionslist (id INT NOT NULL PRIMARY KEY AUTO_INCREMENT, '
                                'tstamp TIMESTAMP, taskid INT, FOREIGN KEY (taskid) REFERENCES tasklist(id), '
                                'actionby SMALLINT, actiontype TINYINT, action TEXT, assignedto SMALLINT, '
                                'pendclosedate DATETIME)')
        self.sql_database.commit()


def change_datetime_format(datetime_object, dtformat, give='datetime'):
    #if datetime_object is None:
    #    return None
    #datetime_object = datetime.datetime.strptime(datestring, '%Y-%m-%d %H:%M:%S')
    if give == 'datetime':
        return datetime_object.strftime(dtformat)
    elif give == 'date':
        return datetime_object.strftime(dtformat.split()[0])
    elif give == 'time':
        return datetime_object.strftime(dtformat.split()[1])
    else:
        return None

def change_datetime_format2(datetime_object, dtformat, give='datetime'):
    if datetime_object is None:
        return None
    datetime_object = datetime.datetime.strptime(datetime_object, '%Y-%m-%d %H:%M:%S')
    if give == 'datetime':
        return datetime_object.strftime(dtformat)
    elif give == 'date':
        return datetime_object.strftime(dtformat.split()[0])
    elif give == 'time':
        return datetime_object.strftime(dtformat.split()[1])
    else:
        return None

#################################################################################################################


class ObjectManager(object):
    def __init__(self, sql_db_object):
        self.sql_database = sql_db_object
        self.sql_cursor = self.sql_database.cursor()

    def list_objects(self, deleted=False):
        if not deleted:
            self.sql_cursor.execute('SELECT id, number, name, region, city, street, house, flat, deleted '
                                    'FROM objectlist WHERE deleted = 0')
        else:
            self.sql_cursor.execute('SELECT id, number, name, region, city, street, house, flat, deleted '
                                    'FROM objectlist WHERE deleted = 1')
        result = self.sql_cursor.fetchall()
        return result

    def search_objects(self, phrase, search_by='number', strict=False, deleted=False):
        if deleted:
            deleted = 1
        else:
            deleted = 0
        if search_by == 'number':
            phrase = phrase.lower()
            if strict:
                query1 = 'SELECT id, number, name, region, city, street, house, flat, deleted FROM objectlist WHERE ' \
                         'lower(number) = "%s" AND deleted = %d LIMIT 50' % (phrase, deleted)
            else:
                query1 = 'SELECT id, number, name, region, city, street, house, flat, deleted FROM objectlist WHERE ' \
                         'lower(number) LIKE "%s%%" AND deleted = %d LIMIT 50' % (phrase, deleted)
        elif search_by == 'id':
            query1 = 'SELECT id, number, name, region, city, street, house, flat, deleted FROM objectlist WHERE ' \
                     'id = %d LIMIT 1' % int(phrase)
        else:
            return None
        self.sql_cursor.execute(query1)
        result = self.sql_cursor.fetchall()
        if result:
            return result
        else:
            return None

    def get_object_data(self, oid):

        self.sql_cursor.execute('SELECT id, number, name, region, city, street, house, flat, deleted, contract, sim1, '
                                'sim2, device1, device2, comm1, comm2 FROM objectlist WHERE id = %d' % oid)
        result = self.sql_cursor.fetchall()
        return result

    def prepare_data(self, input_data):
        objects_data = {}
        for index, data in enumerate(input_data):
            objects_data[index] = {}
            objects_data[index]['id'] = data[0]
            objects_data[index]['number'] = data[1]
            objects_data[index]['name'] = data[2]
            objects_data[index]['address'] = data[3] + ((', ' + data[4]) if data[4] != data[3] else '') + ', ' + \
                                             data[5] + ', ' + data[6] + (('/' + data[7]) if data[7]
                                                                          is not None else '')
            objects_data[index]['deleted'] = False if data[8] == 0 else True
            if len(data) > 9:
                objects_data[index]['contract'] = data[9]
                objects_data[index]['sim'] = '' if data[10] is None else '0' + str(data[10]) + ((', 0' + str(data[11]))
                                                                                            if data[11] != 0 else '')
                objects_data[index]['device'] = data[12] + ((', ' + data[13]) if data[13] is not None else '')
                objects_data[index]['comm'] = '' if data[14] is None else data[14] + ((', ' + data[15]) if data[15]
                                                                                              is not None else '')
        return objects_data

    def new_object(self, data):
        self.sql_cursor.execute('SET NAMES utf8;')
        self.sql_cursor.execute('SET CHARSET utf8;')
        self.sql_cursor.execute('INSERT INTO objectlist (number, deleted, name, region, city, street, house, flat, '
                                'contract, sim1, sim2, device1, device2, comm1, comm2) '
                                'VALUES ("{0:s}", 0, "{1:s}", "{2:s}", "{3:s}", "{4:s}", "{5:s}", "{6:s}", "{7:s}", '
                                '"{8}", "{9}", "{10:s}", "{11:s}", "{12:s}", "{13:s}")'
                                .format(data['number'], data['name'], data['region'], data['city'], data['street'],
                                        data['house'], data['flat'], data['contract'], data['sim1'], data['sim2'],
                                        data['device1'], data['device2'], data['comm1'], data['comm2']))
        self.sql_database.commit()

    def setup_database(self):
        self.sql_cursor.execute('CREATE TABLE objectlist (id INT NOT NULL PRIMARY KEY AUTO_INCREMENT, '
                                'number VARCHAR(8), deleted TINYINT, name VARCHAR(100), region VARCHAR(25), '
                                'city VARCHAR(20), street VARCHAR(25), house VARCHAR(4), flat VARCHAR(6), '
                                'contract VARCHAR(10), sim1 INT, sim2 INT, device1 VARCHAR(20), '
                                'device2 VARCHAR(20), comm1 VARCHAR(20), comm2 VARCHAR(20))')
        self.sql_database.commit()

##################################################################################################################

user_manager = UserManager(USER_DB_FILENAME)
#  user_manager.new_user('admin', 'admin', 0)

object_manager = ObjectManager(sql_database)
task_admin = TaskAdmin(sql_database)

##################################################################################################################


@app.route('/')
def home_page():
    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['submit'] == 'button1':
            name = request.form.get('User_name')
            passwd = request.form.get('Password')
            if user_manager.check_login(name, passwd):
                login_user(user_manager.get_user(name=name))
                return redirect(url_for('home_page'))
            else:
                flash('Invalid Username or Password!')
                return render_template('login.html')
    return render_template('login.html')


@app.route('/logout', )
def logout():
    logout_user()
    return redirect(url_for('home_page'))


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/system_use')
def system_use():
    systeminfo_database = SysinfoDatabase(DATABASE_FILE_NAME, DATETIME_FORMAT)
    select_result = systeminfo_database.select()
    averaging_result, periods_in_avg_result = systeminfo_database.average(select_result)

    html_table = ''
    avg_res_timestamps = averaging_result.keys()
    avg_res_timestamps.sort(reverse=True)
    for index, timestamp_key in enumerate(avg_res_timestamps):  # 5 - table size limit
        html_table = extend_html_table(html_table, averaging_result[timestamp_key], timestamp_key)
        if index >= 4:
            break
    return render_template('system_use.html', html_table=html_table)


@app.route('/special')
def special():
    return render_template('special.html')


@app.route('/task_list')
def task_list():
    task_data = task_admin.get_active_tasks()
    task_details = task_admin.prepare_data(task_data)
    task_details_keys = task_details.keys()
    task_details_keys.sort()
    return render_template('task_list.html', data=task_details, data_keys=task_details_keys)


@app.route('/task_detail/<int:task_id>')  # Not finished yet!!!
def task_detail(task_id):

    task_data, actions_data = task_admin.get_task_details(task_id)
    task_details = task_admin.prepare_data(task_data)[0]

    actions_data = [['2016-06-13 12:33:48', 16, 1, 'Тривога на обєкті, зона номер 7 13.06.2016 о 00.12', 1, None],
                    ['2016-06-14 12:13:29', 16, 2, 'повторна тривога, з 8 13.06.2016 в 00.12', 1, None],
                    ['2016-06-15 09:12:14', 16, 3, 'просто інфа', 1, None],
                    ['2016-06-15 09:12:14', 16, 4, 'передано admin', 1, None]                ]

    actions_details = {}
    for index, action_data in enumerate(actions_data):
        actions_details[index] = {}
        actions_details[index]['action_date'] = change_datetime_format2(action_data[0], DATETIME_FORMAT)
        actions_details[index]['action_by'] = user_manager.get_username(action_data[1]).decode('utf-8')
        actions_details[index]['action_type'] = ACTION_TYPES[action_data[2]].decode('utf-8')
        actions_details[index]['action_type_num'] = action_data[2]
        actions_details[index]['action_text'] = action_data[3].decode('utf-8')
        if action_data[2] == 1 or action_data[2] == 4:
            actions_details[index]['assigned_to'] = user_manager.get_username(action_data[4]).decode('utf-8')
        else:
            actions_details[index]['assigned_to'] = ''
        if action_data[2] == 6:
            actions_details[index]['pendclose_date'] = change_datetime_format2(action_data[5], DATETIME_FORMAT)
        else:
            actions_details[index]['pendclose_date'] = ''

    actions_details_keys = actions_details.keys()
    actions_details_keys.sort()
    return render_template('task_detail.html', task_details=task_details, actions_details=actions_details,
                           actions_keys=actions_details_keys)


@app.route('/create_task', methods=['POST', 'GET'])
def create_task():
    number_sr = False
    number_fnd = False
    input_err = False
    if request.method == 'POST':
        if request.form['submit'] == 'button1':
            number_sr = True
            number = request.form.get('number').encode('utf-8')
            strict_src = request.form.get('strict')
            search_result = object_manager.search_objects(number, strict=strict_src)
            if search_result is not None:
                number_fnd = True
                objects_data = object_manager.prepare_data(search_result)
                data_index = objects_data.keys()
                data_index.sort()
                return render_template('create_task.html', number_sr=number_sr, number_fnd=number_fnd,
                                       data=objects_data, data_index=data_index)
            return render_template('create_task.html', number_sr=number_sr, number_fnd=number_fnd)

        elif request.form['submit'] == 'button2':
            number_fnd = True
            number_sr = True
            task_data = {'objectid': int(request.form.get('objectid').encode('utf-8')),
                         'creator': 1, ####
                         'eventtype': int(request.form.get('eventtype').encode('utf-8')),
                         'event': request.form.get('event').encode('utf-8'),
                         'eventdateraw': request.form.get('eventdate'),
                         'eventtimeraw': request.form.get('eventtime'),
                         'penddateraw': request.form.get('penddate'),
                         'assignedto': int(request.form.get('assignedto').encode('utf-8')),
                         'priority': int(request.form.get('priority').encode('utf-8')),
                         'suspend': request.form.get('suspend'),
                         'status': 5 if not request.form.get('suspend') else 3
                         }
            try:
                task_data['eventdate'] = datetime.datetime.strptime('%s' % (request.form.get('eventdate') + ' ' +
                                                                            request.form.get('eventtime')),
                                                                    '%d.%m.%Y %H.%M')
            except ValueError:
                task_data['eventdate'] = None
                err_message = 'Невірно задано дату або час події!'.decode('utf-8')
                input_err = True
            if request.form.get('suspend'):
                try:
                    task_data['pendclosedate'] = datetime.datetime.strptime('%s' % request.form.get('penddate'),
                                                                            '%d.%m.%Y')
                except ValueError:
                    task_data['pendclosedate'] = None
                    err_message = 'Невірно задано дату відтермінування завдання!'.decode('utf-8')
                    input_err = True
            else:
                task_data['pendclosedate'] = None
            if input_err:
                search_result = object_manager.search_objects(task_data['objectid'], strict=True, search_by='id')
                objects_data = object_manager.prepare_data(search_result)[0]
                return render_template('create_task.html', number_sr=number_sr, number_fnd=number_fnd,
                                       input_err=input_err, err_message=err_message, data=objects_data,
                                       task_data=task_data)
            task_admin.new_task(task_data)
            return render_template('home.html')

    return render_template('create_task.html', number_sr=number_sr, number_fnd=number_fnd)


@app.route('/objects_list')
def objects_list():
    data = object_manager.list_objects()
    objects_data = object_manager.prepare_data(data)
    objects_data_index = objects_data.keys()
    objects_data_index.sort()
    return render_template('objects_list.html', objects_data=objects_data, objects_index=objects_data_index)


@app.route('/object_details/<int:object_id>')
def object_details(object_id):
    data = object_manager.get_object_data(object_id)
    object_data = object_manager.prepare_data(data)[0]
    return render_template('object_details.html', object_data=object_data)


@app.route('/create_object', methods=['GET', 'POST'])
@login_required
def create_object():
        number_chk = False
        if request.method == 'POST':
            if request.form['submit'] == 'button1':
                number = request.form.get('number')
                session['number'] = number
                number_chk = True
                number_free = True
                return render_template('create_object.html', number_chk=number_chk, number_free=number_free,
                                       number=number)
            elif request.form['submit'] == 'button2':
                number = session['number']
                data = {'number': number, 'name': (request.form.get('name')).encode('utf-8'),
                        'region': (request.form.get('region')).encode('utf-8'),
                        'city': (request.form.get('city')).encode('utf-8'),
                        'street': (request.form.get('street')).encode('utf-8'),
                        'house': (request.form.get('house')).encode('utf-8'),
                        'flat': (request.form.get('flat')).encode('utf-8'),
                        'contract': (request.form.get('contract')).encode('utf-8'), 'sim1': request.form.get('sim1'),
                        'sim2': request.form.get('sim2'), 'device1': (request.form.get('device1')).encode('utf-8'),
                        'device2': (request.form.get('device2')).encode('utf-8'),
                        'comm1': (request.form.get('comm1')).encode('utf-8'),
                        'comm2': (request.form.get('comm2')).encode('utf-8')}

                object_manager.new_object(data)
                number_chk = True
                number_free = True
                return render_template('create_object.html', number_chk=number_chk, number_free=number_free,
                                       number=number)
        else:
            return render_template('create_object.html', number_chk=number_chk)


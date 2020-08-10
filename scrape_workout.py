from datetime import datetime  # for the date/time
import datetime, pytz, holidays
from selenium import webdriver
from time import sleep
from credentials import email, password
from selenium.webdriver.common.action_chains import ActionChains
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pprint


class WorkoutLog:
    def __init__(self, email, password, log_website='https://tinyurl.com/MIT-summer2020-training-log', first_unfilled='08/09'):
        self.driver = webdriver.Chrome('/Users/dsert/Desktop/chromedriver')
        self.email = email
        self.driver.get('https://strava.com')
        sleep(5)

        # find "Log In"
        email_button_click = self.driver.find_element_by_xpath("//a[@href='/login']").click()


        sleep(5)

        # handle username
        email_field = self.driver.find_element_by_xpath("//input[@name=\"email\"]")
        email_field.send_keys(email)

        # handles password
        password_field = self.driver.find_element_by_xpath("//input[@name=\"password\"]")
        password_field.send_keys(password)

        # submit credentials
        self.driver.find_element_by_xpath('//button[@type="submit"]').click()
        sleep(6)


        # navigate to training log
        action = ActionChains(self.driver)
        first_menu = self.driver.find_element_by_xpath("//a[@href='/athlete/training/log']")
        action.move_to_element(first_menu).perform()
        sleep(1)
        second_menu = self.driver.find_element_by_xpath("//a[@href='/athlete/training']")
        action.move_to_element(second_menu)
        sleep(1)
        second_menu.click()

        sleep(3)











        # log to second_website: GOOGLE DOCS SPECIFIC CREDENTIALS

        # authorize Python Web Client w/ Google
        scope = ['https://spreadsheets.google.com/feeds']

        creds = ServiceAccountCredentials.from_json_keyfile_name('WorkoutLog-a4ad26937ad6.json', scope)

        client = gspread.authorize(creds)

        sheet =  client.open_by_url('https://docs.google.com/spreadsheets/d/1wDG2qWrxh6JIxP6XFnE68UnF-sWFpYnTyKzTk0UPpH8/edit#gid=1703226110')

        # sheet = client.open_by_url('https://docs.google.com/spreadsheets/d/1XQhytPfJ52cyPRc1WL2G7BeIaXarFKCF6xNgzoY2aJA/edit?usp=sharing')

        date = 0
        current_iteration = ''

        # ** CHECK 1ST BLANK CELL **
        # sheet_info = sheet.worksheet('COVID-69').get_all_values()
        # first_unfilled_date = self.first_unfilled_date(sheet_info)
        first_unfilled_date = first_unfilled
        print('First unfilled date: ', first_unfilled_date)




        # ** IMPORT WORKOUTS FROM STRAVA **
        # todays_date = str(datetime.datetime.strptime(str(date.today()), '%Y-%m-%d').strftime('%d/%m/%y'))
        todays_date = datetime.datetime.today().strftime('%d-%m-%Y')
        current_date = todays_date
        activities = []
        dates_to_workouts = []

        # date: ['Name', 'type', 'duration', 'speed']
        # makes a list of dicts which represent single activities
        print('Collecting workouts..\n\n')
        while not date_in_collected(first_unfilled_date, dates_to_workouts):
            # collect workouts on this page
            activities = self.driver.find_elements_by_class_name("training-activity-row")
            dates_to_workouts += [parse_strava_text_summary(activity.text) for activity in activities]

            # pp = pprint.PrettyPrinter()
            # pp.pprint(dates_to_workouts)

            # skip to next page
            self.driver.find_element_by_xpath('//button[@href="#"]').click()

            sleep(5) # wait 5 sec for page to refresh

        print('Finished collecting workouts \n\nTransferring to Google Doc..')


        # ** POST WORKOUTS TO GOOGLE DOC **
        # find the row, col of the first unfilled date
        worksheet = sheet.worksheet('COVID-69')
        first_unfilled_row_col = worksheet.find(first_unfilled_date) # break into .row, .col


        while dates_to_workouts: # while workouts are still in list

            # pop a workout from list
            workout = dates_to_workouts.pop()

            rowcol = worksheet.find(workout['date'])

            # get row, cell
            row, cell = rowcol.row, rowcol.col

            # fill row with Strava-imported workout information
            self.post_workout_to_row(worksheet, row, workout)
            print('Added: ', workout['name'])



        # ** DONE **
        print('Finished updating google sheet w/Strava workouts.')


    def first_unfilled_date(self, sheet_info):
        '''returns the first unfilled date in the workout doc'''
        for i in range(11, len(sheet_info)):
            if sheet_info[i][1] == '' and sheet_info[i][0]:
                return sheet_info[i][0]




    def post_workout_to_row(self, sheet, row, workout):
        '''posts a single workout to a row
        Note: assume the correct row has already been found

        workout: dict
        sheet = gspread worksheet
        row: XX

        Use this to update cell: worksheet.update_cell(1, 2, 'Bingo!')
        '''
        # the column the data will be written into depending on the workout


        col_for_data = {'date': 1,
                    'name': 2,
                    'Row/Erg (mins)': 3,
                    'Aviron': 3,
                    'Swim/Run (mins)': 4,
                    'Course': 4,
                    'Bike/Other SS (mins)': 5,
                    'Vélo': 5,
                    'Jump Rope/Stairs (mins)': 6,
                    'AT (1 or 0)': 7,
                    'Lifting (mins)': 8,
                    'core (mins)': 9,
                    'Entraînement': 9,
                    'Stretch (1 or 0)': 10}

        # update name if it doesn't already have a name
        if not sheet.cell(row, col_for_data['name']).value:
            sheet.update_cell(row, col_for_data['name'], workout['name'])

        # update correct type workout with duration
        try:
            sheet.update_cell(row, col_for_data[workout['type']], workout['duration'])

        except Exception as e:
            print('Exception: ', e)
            print('The input that caused the exception was: ', workout)
            print('It has been skipped')
        # if it's a classic AT workout, tick AT as 1
        if is_AT(workout['duration']): # so it doesn't take just any 16:XX workout
            sheet.update_cell(row, col_for_data['AT (1 or 0)'], 1)

        sheet.update_cell(row, col_for_data['Stretch (1 or 0)'], 1)


def is_AT(workout_duration):
    '''if it's a classic AT workout (16 min, 6 min 40 sec, etc),
    return True. otherwise return False'''
    return True if workout_duration == 16 or round(workout_duration, 2) == 6.67 or workout_duration == 6 else False

def date_in_collected(target_date, dict_list):
    '''returns True if the passed in date is in the collected workouts'''
    if not dict_list:
        return False
    dates = [dict_['date'] for dict_ in dict_list]
    if target_date in dates:
        return True
    elif dates[-1][0:2] < target_date[0:2] or dates[-1][-2:] < target_date[-2:]:
            return True
    else:
        return False


def parse_strava_text_summary(text):
    '''separates the single string summary into a dictionary of
    date:
    type:
    name:
    duration:
    rate:

    returns dict
    '''

    def is_a_date(possible_date):
        '''returns True if the string is a date'''

        try:
            date_time_obj = datetime.datetime.strptime(possible_date, '%d/%m/%Y')
            return True
        except:
            return False

    def is_a_workout_type(string):
        '''returns True if the string is a workout type'''
        workout_types = {'Aviron', 'Row/Erg (mins)', 'Rowing', 'Course', 'Swim/Run (mins)', 'Bike/Other SS (mins)', 'Vélo', 'Bike/Other SS (mins)', 'Running', 'Entraînement', 'core (mins)', 'Training'}
        return True if string in workout_types else False

    def is_a_time(possible_time):
        '''returns True if the string is a date'''

        try:
            date_time_obj = datetime.datetime.strptime(possible_time, '%H:%M:%S')
            if date_time_obj: # if the string can be represented as a time greater than an hour: X:XX:XX
                return True
            return False
        except ValueError:
            try: # the string-time could be less than an hour: XX:XX
                input_time = possible_time
                t = input_time.split(':')

                total_minutes = int(t[0]) + int(t[1]) / 60

                return total_minutes
            except: # the string is not a time
                return False

    # this is because my computer is set to French, so Strava workouts need to be translated to Google Doc Layout
    french_to_english = {'Course':'Swim/Run (mins)',
                         'Aviron':'Row/Erg (mins)',
                         'Entraînement': 'core (mins)',
                         'Vélo': 'Bike/Other SS (mins)'}
    res = {}
    name = str()
    name_bool = False
    text = text.split()
    for i, elt in enumerate(text):
        if is_a_workout_type(elt):
            try:
                res['type'] = french_to_english(elt)
            except:
                res['type'] = elt
            if elt == 'Entraînement':
                res['name'] = 'abs'
            continue
        if is_a_date(elt): # parses dates
            date = datetime.datetime.strptime(elt, '%d/%m/%Y')
            date_string = datetime.date.strftime(date, '%m/%d')
            res['date'] = date_string
            name_bool = True
            continue
        if is_a_time(elt): # parses time
            res['duration'] = convert_time_to_minutes(elt)
            name_bool = False
        # not a workout type or a date
        if name_bool:
            if not is_a_time(elt):
                name = name + ' ' + elt
                continue

        try:
            if not res['name']:
                res['name'] = name # collects the name of the workout, since the length of the name is variable
        except KeyError:
            res['name'] = name
    return res

def is_a_date(possible_date): # in this scope for testing purposes
    '''returns True if the string is a date'''

    try:
        date_time_obj = datetime.datetime.strptime(possible_date, '%d/%m/%Y')
        return True
    except:
        return False

def is_a_workout_type(string): # in this scope for testing purposes
    '''returns True if the string is a workout type'''
    workout_types = {'Aviron', 'Rowing', 'Course', 'Running', 'Entraînement', 'Training'}
    return True if string in workout_types else False

def is_a_time(possible_time): # in this scope for testing purposes
    '''returns True if the string is a date'''

    try:
        date_time_obj = datetime.datetime.strptime(possible_time, '%H:%M:%S')
        if date_time_obj:
            return True
        return False
    except:
        input_time = possible_time
        t = input_time.split(':')


        total_minutes = int(t[0])  + int(t[1])/60

        return total_minutes

    return False



def convert_time_to_minutes(time_string):
    '''converts time in 'h:mm:ss' to minutes'''
    try: # HH:MM:SS
        hours = time_string[0:2]
        if ':' in hours:
            hours = hours.replace(':', '')

        return round(int(hours)*60 + int(time_string[2:4]) + int(time_string[5:])/60, 4)

    except ValueError: # MM:SS
        mins = time_string[0:2]
        if ':' in mins:
            mins = mins.replace(':', '')

        return round(int(mins) + int(time_string[3:])/60, 4)

if __name__ == "__main__":
    w1 = WorkoutLog(email, password, '07/09')

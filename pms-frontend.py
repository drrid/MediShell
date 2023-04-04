from textual.app import App
from textual.screen import Screen
from textual.widgets import Static, Footer, Header, Input, DataTable, Button
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual import events
import conf
import csv
import io
import datetime as dt
import calendar
from dateutil import parser


# Custom Calendar DataTable ---------------------------------------------------------------------------------------------------------------------------------------------
class CalTable(DataTable):
    def watch_cursor_cell(self, old, value):
        try:
            self.screen.change_week(self.screen.week_index)
            selected_cell = self.data[self.cursor_cell.row][self.cursor_cell.column]
            pt_table = self.screen.create_find_pt()
            enc_table = self.screen.create_find_enc()

            if self.cursor_cell.column > 0 and '_' not in selected_cell:
                pt_id = int(selected_cell.split(' ')[-2])
                selected_pts_list = conf.select_one_id(pt_id)
                rows = csv.reader(io.StringIO(str(selected_pts_list)))
                pt_table.add_rows(rows)
                self.screen.show_encounters(pt_table.data[0][0])
            else:
                self.screen.show_patients()
        except Exception as e:
            self.screen.log_error(e)

        return super().watch_cursor_cell(old, value)

# Custom Patient DataTable ---------------------------------------------------------------------------------------------------------------------------------------------
class PatientTable(DataTable):
    def watch_cursor_cell(self, old, value):
        try:
            self.screen.change_week(self.screen.week_index)
            pt_id = self.data[self.cursor_cell.row][0]
            enc_table = self.screen.create_find_enc()
            self.screen.show_encounters(pt_id)
        except Exception as e:
            self.screen.log_error(e)
        return super().watch_cursor_cell(old, value)

# Custom Encounter DataTable ---------------------------------------------------------------------------------------------------------------------------------------------
class EncounterTable(DataTable):
    def watch_cursor_cell(self, old, value):
        try:
            if self.cursor_cell.column in [2, 3, 4]:
                self.screen.change_week(self.screen.week_index)
                enc_notes = self.data[self.cursor_cell.row][self.cursor_cell.column]
                self.screen.query_one('#notes').focus()
        except Exception as e:
            self.screen.log_error(e)
        return super().watch_cursor_cell(old, value)

# Calendar Screen --------------------------------------------------------------------------------------------------------------------------------------------------
class Calendar(Screen):
    BINDINGS = [("f5", "clear_all()", "Clear"),
                ("f2", "modify_patient()", "Modify Patient"),
                ("f9", "toggle_dark()", "Toggle Dark Mode")]

    week_index = reactive(0)
    selected_value = reactive([])
    selected_value2 = reactive([])
    pt_id = reactive(0)
    
    def compose(self):
        yield Footer()
        self.calendar_table = CalTable(fixed_columns=1, zebra_stripes=True, id='cal_table')
        self.encounter_table = EncounterTable(fixed_columns=1, zebra_stripes=True, id='enc_table')
        self.patient_table = PatientTable(fixed_columns=1, zebra_stripes=True, id='pt_table')

        # self.widget1.styles.background = 'teal'
        # self.widget1.styles.border = ("heavy", "Teal")
        # self.widget1.border_title = 'Cal'
        yield Container(
                Vertical(Horizontal(
                        Input('', placeholder='First Name', id='fname'),
                        Input('', placeholder='Last Name', id='lname'),
                        Input('', placeholder='Phone', id='phone'),
                        Input('', placeholder='Date Of Birth', id='dob'),
                        Button('Add', id='addpatient'),
                        Button('Update', id='updatepatient'), id='inputs'),
                    id='upper_cnt'
                ),
                Vertical(
                    Horizontal(
                        Vertical(self.patient_table,
                                self.encounter_table,
                                Input(placeholder='Notes...', id='notes'), 
                                Static(id='feedback'),
                                id='tables'),
                                self.calendar_table,
                        id='tables_cnt'
                    ),
                    id='lower_cnt'
                ),
                id='app_grid'
            )

    def log_error(self, message):
        self.query_one('#feedback').update(f'[bold red]{str(message)}')


    def on_mount(self):
        # pass
        self.change_week(self.week_index)
        self.create_find_pt()
        self.create_find_enc()
        self.show_patients()

    def action_clear_all(self):
        for inp in self.query(Input):
            inp.value = ''
        self.show_patients()


    def action_modify_patient(self):
        try:
            table = self.query_one('#pt_table')
            row = table.cursor_cell.row
            patient_id = table.data[row][0]
            self.query_one('#fname').value = table.data[row][1]
            self.query_one('#lname').value = table.data[row][2]
            self.query_one('#phone').value = table.data[row][4]
            self.query_one('#dob').value = table.data[row][3]
            self.pt_id = int(table.data[row][0])
        except Exception as e:
            self.screen.log_error(e)

    def on_input_changed(self, event: Input.Changed):
        if event.sender.id in ['fname', 'lname', 'phone']:
            self.show_patients()

    def show_encounters(self, pt_id):
        try:
            if pt_id:
                enc_table = self.create_find_enc()
                selected_pts_list2 = conf.select_all_pt_encounters(int(pt_id))
                if selected_pts_list2:
                    rows = csv.reader(io.StringIO("\n".join([str(r) for r in selected_pts_list2])))
                    for ro in rows:
                        enc_table.add_row(*ro, height=int(len(ro[2])/20+1))
        except Exception as e:
            self.screen.log_error(e)


    def show_patients(self):
        try:
            table = self.create_find_pt()
            fname = self.query_one('#fname').value
            lname = self.query_one('#lname').value
            phone = self.query_one('#phone').value
            if phone.isdigit():
                phone = int(phone)
            else:
                self.query_one('#phone').value = ''

            selected_pts_list = conf.select_all_starts_with_all_fields(fname, lname, phone)
            if selected_pts_list:
                table.add_rows(csv.reader(io.StringIO("\n".join([str(r) for r in selected_pts_list]))))
        except Exception as e:
            self.screen.log_error(e)


    def on_input_submitted(self, event: Input.Submitted):
        try:
            if event.sender.id == 'notes':
                enc_table = self.query_one('#enc_table')
                pt_table = self.query_one('#pt_table')
                cursor = enc_table.cursor_cell.column
                encounter_id = int(enc_table.data[enc_table.cursor_cell.row][0])
                pt_id = int(pt_table.data[pt_table.cursor_cell.row][0])

                if cursor == 2:
                    note = self.query_one('#notes').value
                    conf.update_note(encounter_id, note)
                    self.show_encounters(pt_id)
                    self.query_one('#notes').value = ''
                if cursor == 3:
                    cost = int(self.query_one('#notes').value)
                    conf.update_payment(encounter_id, cost)
                    self.show_encounters(pt_id)
                    self.query_one('#notes').value = ''
                if cursor == 4:
                    fee = int(self.query_one('#notes').value)
                    conf.update_fee(encounter_id, fee)
                    self.show_encounters(pt_id)
                    self.query_one('#notes').value = ''    

            if event.sender.id in ['fname', 'lname', 'phone', 'dob']:
                table = self.query_one('#pt_table')
                fname = self.query_one('#fname').value
                lname = self.query_one('#lname').value
                phone = self.query_one('#phone').value

                if fname == '' and lname == '' and phone == '':
                    return
                if '_' not in self.selected_value:
                    return
                if not self.selected_value:
                    return
                if len(table.data) == 0:
                    return
                if len(table.data) > 1:
                    self.query_one('#pt_table').focus()
                    return
                if len(table.data) == 1:
                    self.selected_value2 = [0, 0, 0]
                    self.submit_patient()
        except Exception as e:
            self.screen.log_error(e)


    def on_button_pressed(self, event: Button.Pressed):
        try:
            if event.sender.id == 'addpatient':
                try:
                    fname = str(self.query_one('#fname', Input).value).capitalize()
                    lname = str(self.query_one('#lname', Input).value).capitalize()
                    phone = int(self.query_one('#phone', Input).value)
                    date_of_birth = parser.parse(str(self.query_one('#dob', Input).value))

                    conf.save_to_db(conf.patient(first_name=fname, 
                                    last_name=lname, 
                                    phone=phone, 
                                    date_of_birth=date_of_birth))

                    self.query_one('#feedback').update(f'Patient Added: {fname} {lname}')
                    self.show_patients()
                except Exception as e:
                    self.log_error(e)

            if event.sender.id == 'updatepatient':
                patient_id = self.pt_id
                fname = str(self.query_one('#fname', Input).value).capitalize()
                lname = str(self.query_one('#lname', Input).value).capitalize()
                phone = int(self.query_one('#phone', Input).value)
                date_of_birth = parser.parse(str(self.query_one('#dob', Input).value))
                conf.update_patient(patient_id, first_name=fname, last_name=lname, phone=phone, date_of_birth=date_of_birth)
                self.query_one('#feedback').update(f'Patient updated: {fname} {lname}')
                self.show_patients()
        except Exception as e:
            self.screen.log_error(e)


    def change_week(self, week):
        try:
            table = self.query_one('#cal_table')
            table.clear()
            table.columns = []
            start_date, end_date = conf.get_weekly_start_end(week)
            table.add_column('', width=7)
            DAYS = ['Saturday', 'Sunday', 'Monday', 'Tuesday', 'Wednsday', 'Thursday', 'Friday']

            for c, d in enumerate(DAYS):
                today = dt.datetime.today()
                today_midnight = dt.datetime(today.year, today.month, today.day, 0, 0)
                weekday = start_date + dt.timedelta(days=c)
                month = calendar.month_abbr[weekday.month]

                if weekday == today_midnight:
                    table.add_column(f'[bold yellow]{d} {weekday.day} {month}', width=22)
                else:
                    table.add_column(f'[blue]{d} {weekday.day} {month}', width=22)
            
            encounters = conf.select_week_encounters(start_date, end_date)
            csv_rows = conf.get_weekly_encounters_csv(encounters)
            with io.StringIO(csv_rows) as input_file:
                rows = csv.reader(input_file)
                for ro in rows:
                    table.add_row(*ro, height=2)
        except Exception as e:
            self.screen.log_error(e)


    def on_key(self, event: events.Key):
        try:
            if event.key == 'ctrl+left':
                self.week_index -= 1
                self.change_week(self.week_index)

            if event.key == 'ctrl+right':
                self.week_index += 1
                self.change_week(self.week_index)
            
            if event.key == 'ctrl+delete':
                table = self.query_one('#cal_table')
                data = table.data[table.cursor_cell.row][table.cursor_cell.column]

                if data != '_':
                    enc_id = int(data.split(' ')[-1])
                    pt_id = int(data.split(' ')[-2])
                    conf.delete_encounter(enc_id)
                    self.change_week(self.week_index)
                    self.show_encounters(pt_id)
                
            if event.key == 'space':
                table = self.query_one('#cal_table')
                if len(table.data[0]) > 5:
                    selected_v = table.data[table.cursor_cell.row][table.cursor_cell.column]
                    self.selected_value = [table.cursor_cell.row, table.cursor_cell.column, selected_v]
                    if selected_v == '_':
                        self.create_find_pt()
                        for inp in self.query(Input):
                            inp.value = ''
                        self.query_one('#fname').focus()

                else:
                    selected_v2 = table.data[table.cursor_cell.row][table.cursor_cell.column]
                    self.selected_value2 = [table.cursor_cell.row, table.cursor_cell.column, selected_v2]
                    self.submit_patient()
        except Exception as e:
            self.screen.log_error(e)


    def create_find_pt(self):
        try:
            table = self.query_one('#pt_table')
            table.clear()
            table.columns = []
            PT_CLMN = [['ID', 4], ['First Name', 18], ['Last Name', 18], ['Date of Birth', 14], ['Phone', 10]]
            for c in PT_CLMN:
                table.add_column(f'{c[0]}', width=c[1])
            return table
        except Exception as e:
            self.screen.log_error(e)


    def create_find_enc(self):
        try:
            table = self.query_one('#enc_table')
            table.clear()
            table.columns = []
            PT_CLMN = [['ID', 4], ['Encounter', 20], ['Note', 20], ['Payment', 10], ['Trt Cost', 10]]
            for c in PT_CLMN:
                table.add_column(f'{c[0]}', width=c[1])
            return table
        except Exception as e:
            self.screen.log_error(e)


    def submit_patient(self):
        try:
            if ('_' not in self.selected_value) or not self.selected_value:
                return
            
            table = self.query_one('#pt_table')
            selected_patient_id = table.data[self.selected_value2[0]][0]
            finaltime = self.calculate_rdvtime()
            pt_encounter = conf.Encounter(patient_id=selected_patient_id, rdv=finaltime)
            if not conf.select_encounter(pt_encounter):
                conf.save_to_db(pt_encounter)
                self.change_week(self.week_index)
                self.show_encounters(table.data[0][0])
        except Exception as e:
            self.screen.log_error(e)


    def calculate_rdvtime(self):
        try:
            INV_DICT_ROW = {
                0: '9:0', 1: '9:20', 2: '9:40', 3: '10:0',
                4: '10:20', 5: '10:40', 6: '11:0', 7: '11:20',
                8: '11:40', 9: '12:0', 10: '12:20', 11: '12:40',
                12: '13:0', 13: '13:20', 14: '13:40', 15: '14:0',
                16: '14:20', 17: '14:40', 18: '15:0', 19: '15:20',
                20: '15:40'
            }

            start_date, end_date = conf.get_weekly_start_end(self.week_index)
            encounter_date = start_date + dt.timedelta(days=self.selected_value[1]-1)
            hour, minute = INV_DICT_ROW.get(self.selected_value[0]).split(':')
            return dt.datetime(encounter_date.year, encounter_date.month, encounter_date.day, int(hour), int(minute))
        except Exception as e:
            self.screen.log_error(e)


# ------------------------------------------------------------------------Main App-----------------------------------------------------------------------------------------
class PMSApp(App):
    BINDINGS = [("f5", "clear_all()", "Clear"),
            ("f2", "modify_patient()", "Modify Patient"),
            ("f9", "toggle_dark()", "Toggle Dark Mode")]
    CSS_PATH = 'styling.css'
    SCREENS = {"screen1": Calendar()}

    def on_mount(self):
        self.push_screen(self.SCREENS.get('screen1'))

    def action_toggle_dark(self):
        self.dark = not self.dark

if __name__ == "__main__":
    app = PMSApp()
    app.run()

 
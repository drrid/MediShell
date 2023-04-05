from textual.app import App
from textual.screen import Screen
from textual.widgets import Static, Footer, Header, Input, DataTable, Button
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual import events
import conf
import datetime as dt
import calendar
from dateutil import parser


# Calendar Screen --------------------------------------------------------------------------------------------------------------------------------------------------
class Calendar(Screen):
    def compose(self):
        self.table = DataTable()
        self.calendar_widget = DataTable(id='cal_table')
        self.encounter_widget = DataTable(id='enc_table')
        self.patient_widget = DataTable(id='pt_table')
        self.inputs_container = Vertical(Horizontal(
                                Input('', placeholder='First Name', id='fname'),
                                Input('', placeholder='Last Name', id='lname'),
                                Input('', placeholder='Phone', id='phone'),
                                Input('', placeholder='Date Of Birth', id='dob'),
                                Button('Add', id='addpatient'),
                                Button('Update', id='updatepatient'), id='inputs'),
                            id='upper_cnt')
        self.tables_container = Vertical(
                            Horizontal(
                                Vertical(self.patient_widget,
                                        self.encounter_widget,
                                        Input(placeholder='Notes...', id='notes'), 
                                        Static(id='feedback'),
                                        id='tables'),
                                        self.calendar_widget,
                                id='tables_cnt'),
                            id='lower_cnt')
        
        self.footer_widget = Footer()
        yield Container(self.inputs_container,
                        self.tables_container,
                        id='app_grid')


    def on_mount(self):
        self.show_calendar(0)
        self.show_patients(first_name='')
        self.show_encounters(4)


    def show_patients(self, **kwargs):
        patients = conf.select_all_starts_with(**kwargs)
        patients.insert(0, ('ID', 'First Name', 'Last Name', 'Date of Birth', 'Phone'))
        patients = iter(patients)
        table = self.query_one('#pt_table')
        table.add_columns(*next(patients))
        table.add_rows(patients)

    def show_encounters(self, pt_id):
        encounters = conf.select_all_pt_encounters(pt_id)
        encounters.insert(0, ('ID', 'Encounter', 'Note', 'Payment', 'Fee'))
        encounters = iter(encounters)
        table = self.query_one('#enc_table')
        table.add_columns(*next(encounters))
        table.add_rows(encounters)

    def show_calendar(self, week_index):
        schedule = iter(conf.generate_schedule(week_index))
        table = self.query_one('#cal_table')
        table.add_columns(*next(schedule))
        table.add_rows(schedule)

    def on_data_table_cell_selected(self, message: DataTable.CellSelected):
        pass

    

# ------------------------------------------------------------------------Main App-----------------------------------------------------------------------------------------
class PMSApp(App):
    CSS_PATH = 'styling-test.css'
    SCREENS = {"screen1": Calendar()}

    def on_mount(self):
        self.push_screen(self.SCREENS.get('screen1'))

if __name__ == "__main__":
    app = PMSApp()
    app.run()

 
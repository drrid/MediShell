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

    BINDINGS = [("ctrl+right", "next_week", "Next Week"),
                ("ctrl+left", "previous_week", "Previous Week")]
    week_index = reactive(0)

    def compose(self):
        self.table = DataTable()
        self.calendar_widget = DataTable(id='cal_table')
        self.encounter_widget = DataTable(id='enc_table')
        self.patient_widget = DataTable(id='pt_table')
        self.patient_widget.cursor_type = 'row'
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
        
        yield Container(self.inputs_container, self.tables_container, id='app_grid')
        yield self.footer_widget    
    
    def on_mount(self):
        self.patient_widget.add_columns('ID', 'First Name', 'Last Name', 'Date of Birth', 'Phone')
        self.encounter_widget.add_columns('ID', 'Encounter', 'Note', 'Payment', 'Fee')
        self.show_calendar(self.week_index)
        self.show_patients(first_name='')

    def log_error(self, msg):
        self.query_one('#feedback').update(f'[bold red]{str(msg)}')

    def action_next_week(self):
        self.calendar_widget.clear(columns=True)
        self.week_index += 1 
        self.show_calendar(self.week_index)

    def action_previous_week(self):
        self.calendar_widget.clear(columns=True)
        self.week_index -= 1 
        self.show_calendar(self.week_index)

    def log_feedback(self, msg):
        self.query_one('#feedback').update(f'[bold teal]{str(msg)}')

    def show_patients(self, **kwargs):
        patients = iter(conf.select_all_starts_with(**kwargs))
        self.patient_widget.add_rows(patients)

    def show_encounters(self, pt_id):
        encounters = iter(conf.select_all_pt_encounters(pt_id))
        self.encounter_widget.add_rows(encounters)

    def show_calendar(self, week_index):
        schedule = iter(conf.generate_schedule(week_index))
        table = self.query_one('#cal_table')
        table.add_columns(*next(schedule))
        table.add_rows(schedule)

    # def on_data_table_cell_selected(self, message: DataTable.CellSelected):
    #     if message.control.id == 'pt_table':
    #         self.show_encounters(message.cell_key.)

    def on_data_table_row_selected(self, message: DataTable.RowSelected):
        self.encounter_widget.clear()
        pt_id = int(self.patient_widget.get_row(message.row_key)[0])
        self.show_encounters(pt_id)
            

    

# ------------------------------------------------------------------------Main App-----------------------------------------------------------------------------------------
class PMSApp(App):
    CSS_PATH = 'styling.css'
    SCREENS = {"screen1": Calendar()}

    def on_mount(self):
        self.push_screen(self.SCREENS.get('screen1'))

if __name__ == "__main__":
    app = PMSApp()
    app.run()

 
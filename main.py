from textual.app import App
from textual.screen import Screen
from textual.widgets import Static, Footer, Header, Input, DataTable, Button
from textual.coordinate import Coordinate
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual import events
import conf
import datetime as dt
from dateutil import parser

from datetime import date, time, timedelta


# Calendar Screen --------------------------------------------------------------------------------------------------------------------------------------------------
class Calendar(Screen):

    BINDINGS = [("ctrl+left", "previous_week", "Previous Week"),
                ("ctrl+right", "next_week", "Next Week"),
                ("space", "add_encounter", "Add Encounter")]
    week_index = reactive(0)

    def compose(self):
        self.table = DataTable()
        self.calendar_widget = DataTable(id='cal_table', fixed_columns=1, zebra_stripes=True)
        self.encounter_widget = DataTable(id='enc_table', zebra_stripes=True, fixed_columns=1)
        self.patient_widget = DataTable(id='pt_table', zebra_stripes=True, fixed_columns=1)
        self.patient_widget.cursor_type = 'row'


        self.inputs_container = Vertical(Horizontal(
                                    Input('', placeholder='First Name', id='fname'),Input('', placeholder='Last Name', id='lname'),
                                    Input('', placeholder='Phone', id='phone'),Input('', placeholder='Date Of Birth', id='dob'),
                                    Button('Add', id='addpatient'),Button('Update', id='updatepatient'), id='inputs'),
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
        PT_CLMN = [['ID', 3], ['First Name', 13], ['Last Name', 13], ['Date of Birth', 12], ['Phone', 10]]
        for c in PT_CLMN:
            self.patient_widget.add_column(f'{c[0]}', width=c[1])

        ENC_CLMN = [['ID', 3], ['Encounter', 20], ['Note', 15], ['Payment', 7], ['Fee', 7]]
        for c in ENC_CLMN:
            self.encounter_widget.add_column(f'{c[0]}', width=c[1])

        self.show_calendar(self.week_index)
        self.show_patients(first_name='')

    def on_input_submitted(self, event: Input.Submitted):
        try:
            cursor = self.encounter_widget.cursor_coordinate
            encounter_id = self.encounter_widget.get_cell_at(Coordinate(cursor.row,0))
            input_to_modify = self.query_one('#notes').value

            if cursor.column == 2:
                conf.update_encounter(encounter_id, note=str(input_to_modify))
                self.encounter_widget.update_cell_at(cursor, input_to_modify)
            if cursor.column == 3:
                conf.update_encounter(encounter_id, payment=int(input_to_modify))
                self.encounter_widget.update_cell_at(cursor, input_to_modify)
            if cursor.column == 4:
                conf.update_encounter(encounter_id, treatment_cost=int(input_to_modify))
                self.encounter_widget.update_cell_at(cursor, input_to_modify)
        except Exception as e:
            self.log_error(f"Error updating encounter: {e}")

    def on_button_pressed(self, event: Button.Pressed):
        if event.control.id == 'addpatient':
            first_name = self.query_one('#fname').value
            last_name = self.query_one('#lname').value
            phone = self.query_one('#phone').value
            date_of_birth = self.query_one('#dob').value

            # Validate the input values
            if not first_name or not last_name or not phone or not date_of_birth:
                self.log_error("Please fill in all fields.")
                return

            try:
                parsed_dob = dt.datetime.strptime(date_of_birth, "%Y-%m-%d").date()
            except ValueError:
                self.log_error("Invalid date format. Use YYYY-MM-DD.")
                return
            try:
                parsed_phone = int(phone)
            except ValueError:
                self.log_error("Invalid phone number.")
                return

            self.add_patient(first_name, last_name, parsed_phone, parsed_dob)

    def action_add_encounter(self):
        try:
            cursor = self.calendar_widget.cursor_coordinate
            cursor_value = self.calendar_widget.get_cell_at(cursor)
            if '_' not in cursor_value:
                self.log_error(f"Time slot occupied, please choose another one!")
                return
            
            patient_id = int(self.patient_widget.get_cell_at(Coordinate(self.patient_widget.cursor_coordinate.row, 0)))
            patient_first_name = self.patient_widget.get_cell_at(Coordinate(self.patient_widget.cursor_coordinate.row, 1))
            patient_last_name = self.patient_widget.get_cell_at(Coordinate(self.patient_widget.cursor_coordinate.row, 2))

            selected_datetime = self.get_datetime_from_cell(self.week_index, cursor.row, cursor.column)
            conf.save_to_db(conf.Encounter(patient_id=patient_id, rdv=selected_datetime))

            self.calendar_widget.update_cell_at(cursor, f'{patient_first_name} {patient_last_name}')
            self.encounter_widget.clear()
            self.show_encounters(patient_id)
            self.log_feedback('Encounter added successfully')
        except Exception as e:
            self.log_error(f"Error adding encounter: {e}")


    def get_datetime_from_cell(self,week_index, row, column):
        today = date.today()
        days_to_saturday = (5 - today.weekday()) % 7
        start_date = today + timedelta(days=days_to_saturday) + timedelta(weeks=week_index - 1)
        
        day = start_date + timedelta(days=column - 1)
        time_slot_start, _ = conf.generate_time_slot(9, 0, 20, 21)[row]
        
        return dt.datetime.combine(day, time_slot_start)


    def add_patient(self, first_name, last_name, phone, date_of_birth):
        try:
            patient = conf.patient(first_name=first_name, last_name=last_name, phone=phone, date_of_birth=date_of_birth)
            conf.save_to_db(patient)
            self.log_feedback("Patient added successfully.")
            self.show_patients(first_name='')
        except Exception as e:
            self.log_error(f"Error adding patient: {e}")

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

        # Retrieve the column names from the schedule iterator
        column_names = next(schedule)

        # Iterate over the column names and add them to the table
        for i, column_name in enumerate(column_names):
            if i == 0:
                table.add_column(column_name, width=5)
            else:
                table.add_column(column_name, width=18)

        for row in schedule:
            table.add_row(*row, height=2)
        # table.add_rows(schedule)
        # self.log_feedback()
        self.color_todays_encounters()


    def color_todays_encounters(self):
        table = self.query_one('#cal_table')
        today = dt.datetime.today().date()

        # Iterate through the columns
        for col_idx in range(1, 8):
            column_date = self.get_datetime_from_cell(self.week_index, 3, col_idx).date()

            # Check if the column date is the current day
            if column_date == today:
                # Iterate through the rows
                for row_idx in range(table.row_count):
                    cell = table.get_cell_at(Coordinate(row_idx, col_idx))
                    table.update_cell_at(Coordinate(row_idx, col_idx), f'[bold blue]{cell}')


    def on_data_table_cell_selected(self, message: DataTable.CellSelected):
        if message.control.id == 'enc_table':
            self.query_one('#notes').focus()
            self.query_one('#notes').value = ''

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

 
from textual.app import App
from textual.screen import Screen, ModalScreen
from textual.widgets import Static, Footer, Header, Input, DataTable, Button, RadioButton, RadioSet, Checkbox, ListView, ListItem, Label
from textual.coordinate import Coordinate
from textual.containers import Container, Horizontal, Vertical, VerticalScroll, Grid
from textual.reactive import reactive
import conf
import datetime as dt
from dateutil import parser
import asyncio
import os
# import win32com.client

from datetime import date, timedelta

import openpyxl


medicaments = [
    ('LEXIN 1 g (CP) - 1cp * 2/J', 'lexin'),('BIOROGYL(CP)', 'biorogyl'),('ROVAMYCINE 3M(CP)', 'rovamycine_3m'),
    ('ROVAMYCINE 1.5M(CP)', 'rovamycine_1.5m'),('ROVAMYCINE (SP)', 'rovamycine_sp'),('CLAMOXYL 1 g (CP)', 'clamoxyl_1g'),
    ('CLAMOXYL 500 mg (SIROP) - 1 cuillère * 2/j', 'clamoxyl_500mg_sirop'),('CLAMOXYL 500 mg (INJ)', 'clamoxyl_500mg_inj'),('CLAMOXYL 1 g (INJ)', 'clamoxyl_1g_inj'),
    ('FLAGYL 500 mg (CP)', 'flagyl_500mg'),('FLAGYL 250 mg (CP)', 'flagyl_250mg'),('FLAGYL 125 mg (SP)', 'flagyl_125mg'),
    ('SOLUPRED 20 mg (CP)', 'solupred_20mg'),('DOLIPRANE 1 g (CP)', 'doliprane_1g'),('LOMAC 20mg (gle)', 'lomac_20mg'),
    ('SOLUMEDROL 40 mg (INJ) - 1inj*1/j LE MATIN', 'solumedrol_40mg_inj'),('MAXTRIT BDB - 01 BTE - 1BDB * 2/J', 'maxtrit_bdb'),('NOPAIN DS (CP)', 'nopain_ds'),
    ('RAPIDUS 50 mg (CP)', 'rapidus_50mg'),('SAPOFEN 600 mg(CP)', 'sapofen_600mg'),('SAPOFEN 400 mg(CP)', 'sapofen_400mg'),
    ('SAPOFEN 200 mg(CP)', 'sapofen_200mg'),('ALGIFEN (SP) 1DDP *2/J', 'algifen'),('CODOLIPRANE 1 g (CP)', 'codoliprane_1g'),
    ('NEUROVIT (CP)', 'neurovit'),('VIT C (CP)', 'vit_c'),('AUGMENTIN 1 g (SH)', 'augmentin_1g_sh'),
    ('AUGMENTIN 500 mg (SH)', 'augmentin_500mg_sh'),('AUGMENTIN 100 mg (SP)', 'augmentin_100mg_sp'),('CLOFENAL 100 mg (SUPP)', 'clofenal_100mg_supp'),
    ('CLOFENAL 25 mg (SUPP)', 'clofenal_25mg_supp'),('DOLIPRANE 300 mg (SH)', 'doliprane_300mg_sh'),('DOLIPRANE 300 mg (SUPP)', 'doliprane_300mg_supp')
]

# Export Screen --------------------------------------------------------------------------------------------------------------------------------------------------
class ExportScreen(ModalScreen):

    def compose(self):
        with Grid(id='dialog'):
            with Horizontal(id='selection'):
                with Vertical(id='right_cnt'):
                    with RadioSet(id='exports'):
                        yield RadioButton('Ordonnance', id='export_menu', value=True)
                        yield RadioButton('Pano', id='pano')
                        yield RadioButton('TLR', id='tlr')
                        yield RadioButton('Pano+TLR', id='pano_tlr')
                        yield RadioButton('Certificat', id='certificat')
                        yield RadioButton('Arret 3 jours', id='arret_3jr')
                    yield(Static(id='feedback_popup'))
                with VerticalScroll(id='medicament'):
                    for med_name, med_id in medicaments:
                        yield Checkbox(med_name, id=med_id)

            with Horizontal(id='buttons'):
                yield Button('export', id='export', variant='primary')
                yield Button('print', id='print', variant='primary')
                yield Button('exit', id='exit', variant='error')

    def get_checked_checkboxes(self):
        checked_checkboxes = []
        for checkbox in self.query(Checkbox):
            if checkbox.value:
                checked_checkboxes.append(str(checkbox.label))
        return checked_checkboxes
    
    def get_checked_radiobutton(self):
        for radiobutton in self.query(RadioButton):
            if radiobutton.value:   
                return str(radiobutton.label)
            
    def save_document(self, patient_id, encounter_id, file, prescription=None):
        root = os.path.dirname(os.path.abspath(__file__))
        workbook = openpyxl.load_workbook(f'{root}/templates/{file}.xlsx')
        worksheet = workbook['Sheet1']
        name_cell = worksheet['K8']
        date_cell = worksheet['O8']

        today = dt.date.today()
        formatted_date = today.strftime('%d-%m-%Y')
        patient = conf.select_patient_by_id(patient_id)

        name_cell.value = f'{patient.first_name} {patient.last_name}'
        date_cell.value = formatted_date

        if prescription:
            pres_cell = worksheet['K13']
            pres_cell.value = '\n'.join(prescription)

        document_type = file
        path = conf.save_prescription_file(patient_id, patient.first_name, patient.last_name, encounter_id, document_type, workbook)
        self.log_feedback('Document generated successfully.')
        return path

    def get_selected_data(self):
        calendar_screen = self.app.SCREENS.get('calendar')
        cursor = calendar_screen.calendar_widget.cursor_coordinate
        encounter_time = calendar_screen.get_datetime_from_cell(calendar_screen.week_index, cursor.row, cursor.column)
        encounter = conf.select_encounter_by_rdv(encounter_time)
        return encounter.patient_id, encounter.encounter_id

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ["export", "print"]:
            selected_radiobutton = self.get_checked_radiobutton()
            try:
                patient_id, encounter_id = self.get_selected_data()
            except Exception as e:
                self.log_error(f'Please select an encounter!{e}')
                return

            if selected_radiobutton == 'Ordonnance':
                selected_checkboxes = self.get_checked_checkboxes()
                if len(selected_checkboxes) != 0:
                    try:
                        path = self.save_document(patient_id, encounter_id, selected_radiobutton, selected_checkboxes)
                    except Exception as e:
                        self.log_error(e)
                        return
                else:
                    self.log_error('Please choose a prescription!')
                    return

            elif selected_radiobutton in ['Arret 3 jours', 'Certificat', 'Pano', 'TLR', 'Pano+TLR']:
                try:
                    path = self.save_document(patient_id, encounter_id, selected_radiobutton)
                except Exception as e:
                    self.log_error(e)
                    return

            if event.button.id == 'print':
                try:
                    self.print_excel_file(path)
                except Exception as e:
                    self.log_error(e)

        elif event.button.id == "exit":
            self.app.pop_screen()


    def print_excel_file(self, file_path):
        excel = win32com.client.Dispatch("Excel.Application")
        excel.Visible = False 
        try:
            workbook = excel.Workbooks.Open(file_path)
            workbook.PrintOut()
            workbook.Close(SaveChanges=0)
        finally:
            excel.Quit()


    def log_feedback(self, msg):
        self.query_one('#feedback_popup').update(f'[bold #11696b]{str(msg)}')

    def log_error(self, msg):
        self.query_one('#feedback_popup').update(f'[bold red]{str(msg)}')


# Calendar Screen --------------------------------------------------------------------------------------------------------------------------------------------------
class Calendar(Screen):
    BINDINGS = [("ctrl+left", "previous_week", "Previous Week"),
            ("ctrl+right", "next_week", "Next Week"),
            ("f1", "add_encounter", "Add Encounter"),
            ("ctrl+delete", "delete_encounter", "Delete Encounter"),
            ("f5", "clear_inputs", "Clear"),
            ("f10", "request_export", "Export")]
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
        self.footer_widget.styles.background = '#11696b'

        yield Header()
        yield Container(self.inputs_container, self.tables_container, id='app_grid')
        yield self.footer_widget    
    
    async def update_calendar_periodically(self) -> None:
        while True:
            await asyncio.sleep(60)  # Update every 60 seconds (1 minute)
            self.show_calendar(self.week_index)
            self.color_todays_encounters()

    def refresh_tables(self):
        self.show_calendar(self.week_index)

    def on_mount(self):
        asyncio.create_task(self.update_calendar_periodically())

        PT_CLMN = [['ID', 3], ['First Name', 13], ['Last Name', 13], ['Date of Birth', 12], ['Phone', 10]]
        for c in PT_CLMN:
            self.patient_widget.add_column(f'{c[0]}', width=c[1])

        ENC_CLMN = [['ID', 3], ['Encounter', 12], ['Note', 23], ['Payment', 7], ['Fee', 7]]
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


    def on_input_changed(self, event: Input.Changed):
        try:
            fname = self.query_one('#fname').value
            lname = self.query_one('#lname').value
            phone = self.query_one('#phone').value
            if phone.isdigit():
                phone = int(phone)
            else:
                self.query_one('#phone').value = ''

            patients = iter(conf.select_all_starts_with(first_name=fname, last_name=lname, phone=phone))
            if patients is not None:
                self.patient_widget.clear()
                self.patient_widget.add_rows(patients)
        except Exception as e:
            self.log_error(e)


    def action_clear_inputs(self):
        for input in self.query(Input):
            input.value = ''

    def on_button_pressed(self, event: Button.Pressed):
        if event.control.id == 'addpatient':
            first_name = self.query_one('#fname').value.capitalize()
            last_name = self.query_one('#lname').value.capitalize()
            phone = self.query_one('#phone').value
            date_of_birth = self.query_one('#dob').value

            # Validate the input values
            if not first_name or not last_name or not phone or not date_of_birth:
                self.log_error("Please fill in all fields.")
                return

            try:
                parsed_dob = parser.parse(date_of_birth).date()
            except ValueError:
                self.log_error("Invalid date format.")
                return
            try:
                parsed_phone = int(phone)
            except ValueError:
                self.log_error("Invalid phone number.")
                return

            # Check for patient duplication
            existing_patient = conf.select_patient_by_details(first_name, last_name, parsed_phone, parsed_dob)
            if existing_patient:
                self.log_error("Patient with the same details already exists.")
                return

            self.add_patient(first_name, last_name, parsed_phone, parsed_dob)


    def action_delete_encounter(self):
        cursor = self.calendar_widget.cursor_coordinate
        patient_name = self.calendar_widget.get_cell_at(cursor)
        if '_' in patient_name:
            self.log_error('No encounter to delete!')
            return
        
        try:
            encounter_time = self.get_datetime_from_cell(self.week_index, cursor.row, cursor.column)
            encounter_id = conf.select_encounter_by_rdv(encounter_time).encounter_id
            conf.delete_encounter(encounter_id)
            self.calendar_widget.update_cell_at(cursor, '_')
            self.color_todays_encounters()
            self.encounter_widget.clear()
            self.show_patients(first_name='')
            self.log_feedback('Encounter deleted successfully.')
        except Exception as e:
            self.log_error(e)
            return

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
            self.log_feedback(selected_datetime)
            conf.save_to_db(conf.Encounter(patient_id=patient_id, rdv=selected_datetime))

            self.calendar_widget.update_cell_at(cursor, f'{patient_first_name} {patient_last_name}')
            self.encounter_widget.clear()
            self.show_encounters(patient_id)
            self.color_todays_encounters()
            self.log_feedback('Encounter added successfully')
        except Exception as e:
            self.log_error(f"Error adding encounter: {e}")


    def get_datetime_from_cell(self,week_index, row, column):
        today = date.today()
        # days_to_saturday = (5 - today.weekday()) % 7
        # start_date = today + timedelta(days=days_to_saturday) + timedelta(weeks=week_index)
        days_to_saturday = (today.weekday() - 5) % 7
        start_date = today - timedelta(days=days_to_saturday) + timedelta(weeks=week_index)
        
        day = start_date + timedelta(days=column - 1)
        time_slot_start, _ = conf.generate_time_slot(9, 0, 20, 21)[row]
        
        return dt.datetime.combine(day, time_slot_start)


    def add_patient(self, first_name, last_name, phone, date_of_birth):
        try:
            patient = conf.Patient(first_name=first_name, last_name=last_name, phone=phone, date_of_birth=date_of_birth)
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
        self.query_one('#feedback').update(f'[bold #11696b]{str(msg)}')


    def show_patients(self, **kwargs):
        self.patient_widget.clear()
        patients = iter(conf.select_all_starts_with(**kwargs))
        self.patient_widget.add_rows(patients)

    def show_encounters(self, pt_id, encounter_id='All'):
        self.encounter_widget.clear()
        if encounter_id == 'All':
            encounters = iter(conf.select_all_pt_encounters(pt_id))
            for row in encounters:
                self.encounter_widget.add_row(*row, height=int(len(row[2])/20+1))
        else:
            encounter = iter(conf.select_pt_encounter(encounter_id))
            for row in encounter:
                self.encounter_widget.add_row(*row, height=int(len(row[2])/20+1))

    def show_calendar(self, week_index):
        self.calendar_widget.clear(columns=True)
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
                    table.update_cell_at(Coordinate(row_idx, col_idx), f'[bold yellow]{cell}')


    def on_data_table_cell_selected(self, message: DataTable.CellSelected):
        if message.control.id == 'enc_table':
            self.query_one('#notes').focus()
            self.query_one('#notes').value = ''
        if message.control.id == 'cal_table':
            cursor = self.calendar_widget.cursor_coordinate
            cursor_value = self.calendar_widget.get_cell_at(cursor)
            if '_' in cursor_value or ':' in cursor_value:
                self.show_patients(first_name='')
                self.encounter_widget.clear()
                return
            
            try:
                encounter_time = self.get_datetime_from_cell(self.week_index, cursor.row, cursor.column)
                patient_id = conf.select_encounter_by_rdv(encounter_time).patient_id
                encounter_id = conf.select_encounter_by_rdv(encounter_time).encounter_id
                self.show_patients(patient_id=patient_id)
                self.show_encounters(patient_id, encounter_id=encounter_id)
            except Exception as e:
                self.log_error(e)


    def on_data_table_row_selected(self, message: DataTable.RowSelected):
        self.encounter_widget.clear()
        pt_id = int(self.patient_widget.get_row(message.row_key)[0])
        self.show_encounters(pt_id)
            

    

# ------------------------------------------------------------------------Main App-----------------------------------------------------------------------------------------
class PMSApp(App):
    BINDINGS = [("ctrl+left", "previous_week", "Previous Week"),
            ("ctrl+right", "next_week", "Next Week"),
            ("f1", "add_encounter", "Add Encounter"),
            ("ctrl+delete", "delete_encounter", "Delete Encounter"),
            ("f5", "clear_inputs", "Clear"),
            ("f10", "request_export", "Export")]
    
    CSS_PATH = 'styling.css'
    TITLE = 'TerminalPMS'
    SUB_TITLE = 'by Dr.Abdennebi Tarek'
    SCREENS = {"calendar": Calendar()}

    def on_mount(self):
        self.push_screen(self.SCREENS.get('calendar'))

    def action_request_export(self) -> None:
        self.push_screen(ExportScreen())

if __name__ == "__main__":
    app = PMSApp()
    app.run()

 
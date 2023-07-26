from textual.app import App
from textual.screen import Screen, ModalScreen
from textual.widgets import Static, Footer, Header, Input, DataTable, Button, RadioButton, RadioSet, Checkbox, SelectionList, TextLog, ProgressBar
from textual.coordinate import Coordinate
from textual.containers import Container, Horizontal, Vertical, VerticalScroll, Grid
from textual.reactive import reactive
from textual import work
import conf
import datetime as dt
from dateutil import parser
import asyncio
import os
from natsort import natsorted 
import re
from sys import platform
if platform == 'win32':
    import win32com.client

import paramiko
from dotenv import load_dotenv
from textual.worker import Worker, get_current_worker
import nextcloud_client
import time as tm

from datetime import date, timedelta
import openpyxl


load_dotenv()
passkey = os.getenv('PASSKEY')
host = os.getenv('HOST')
nc_client = os.getenv('NC_CLIENT')
nc_user = os.getenv('NC_USER')
nc_pass = os.getenv('NC_PASS')
special_account = os.getenv('SPECIAL_ACCOUNT')
ubuntu_pass = os.getenv('UBUNTU_PASS')

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
        # self.query_one('#feedback_popup').update(f'[bold #11696b]{str(msg)}')

    def log_error(self, msg):
        self.query_one('#feedback_popup').update(f'[bold red]{str(msg)}')


# Printing Export Screen --------------------------------------------------------------------------------------------------------------------------------------------------
class PrintExportScreen(ModalScreen):

    nb_aligners = []
    worker = []
    
    def compose(self):
        self.selectionlist = SelectionList[int]()
        with Grid(id='dialog'):
            with Horizontal(id='selection'):
                with Vertical(id='right_cnt'):
                    with RadioSet(id='exports'):
                        yield RadioButton('3D models', id='models', value=True)
                        yield RadioButton('Prescription', id='prescription')
                        # yield RadioButton('custom', id='custom')
                        # yield RadioButton('patient', id='pt-select')
                    yield Button('toggle all', id='toggle-all')
                    yield(Static(id='feedback_popup'))
                with VerticalScroll(id='printjobs'):
                    yield self.selectionlist
            with Horizontal(id='progress-pane'):
                yield(ProgressBar(id='progress', total=100))
            with Horizontal():
                yield(TextLog(id='textlog', highlight=True, markup=True))
            with Horizontal(id='buttons'):
                yield Button('export', id='export', variant='primary')
                yield Button('print', id='print', variant='primary')
                yield Button('exit', id='exit', variant='error')


    def on_mount(self):
        self.show_selectionlist()

    def show_selectionlist(self):
        try:
            self.selectionlist.clear_options()
            selected_radio = self.query_one('#exports').pressed_button.id

            if selected_radio == 'models':
                calendar_screen: Calendar = self.app.SCREENS.get('calendar')
                patient = calendar_screen.patient_widget.get_row_at(calendar_screen.patient_widget.cursor_coordinate.row)
                self.selectionlist.border_title = f'{patient[0]} {patient[1]} {patient[2]}'

                if platform == 'darwin':
                    pt_dir = f'/Volumes/mediaserver/patients/{patient[0]} {patient[1]} {patient[2]}'
                else:
                    pt_dir = f'Z:\\patients\\{patient[0]} {patient[1]} {patient[2]}'

                self.nb_aligners = []
                scanned_files = os.listdir(pt_dir)

                for file in natsorted(scanned_files):
                    if file.endswith(f'.stl'):
                        self.nb_aligners.append(file)
                        self.selectionlist.add_option((file.split('_')[-1], file))
                if len(self.nb_aligners) == 0:
                    self.log_feedback('no STL files found!')

            elif selected_radio == 'prescription':
                self.selectionlist.add_option(('Pano', 'pano'))
                self.selectionlist.add_option(('Pano + Teleradiographie', 'pano_tlr'))
                self.selectionlist.add_option(('Certificat', 'certificat'))
                self.selectionlist.add_option(('Empty', 'empty'))

        except Exception as e:
            self.log_error('Error in show_selectionlist: ' + str(e))


    def on_radio_set_changed(self, event: RadioSet.Changed):
        self.show_selectionlist()

    # def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
    #     """Called when the worker state changes."""
    #     if event.state.name == 'SUCCESS':
    #         self.worker.append(event.worker)
    #     if len(self.worker) == len(self.app.workers):
    #         self.query_one('#textlog').write(f'[green]------------------DONE-----------------------------------------------')
    #         self.worker = []
        
    
    def on_button_pressed(self, event: Button.Pressed):
        try:
            if event.button.id in ["export", "print"]:
                self.worker = []
                selected_radio = self.query_one('#exports').pressed_button.id
                if selected_radio == 'models':
                    calendar_screen: Calendar = self.app.SCREENS.get('calendar')
                    patient = calendar_screen.patient_widget.get_row_at(calendar_screen.patient_widget.cursor_coordinate.row)

                    selected_files = []
                    for file in self.selectionlist.selected:
                        filepath = f'/home/tarek/zfsmedia2/patients/{patient[0]} {patient[1]} {patient[2]}/{file}'
                        selected_files.append(filepath)

                    split_selected_files = [selected_files[i:i + 10] for i in range(0, len(selected_files), 10)]  
                    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
                    client = self.connect_to_server()
                    for i, chunk in enumerate(split_selected_files):
                        client = self.connect_to_server()
                        self.query_one('#progress').update(progress=0)
                        pt_name = f"'/home/tarek/zfsmedia2/patients/{patient[0]} {patient[1]} {patient[2]}/{len(selected_files)}-{timestamp}-{i}.sl1'"
                        chunck_joined = "' '".join(chunk)
                        prusa_cmd = "prusa-slicer --export-sla --merge --load config.ini --output"
                        uvtools_cmd =  '/home/tarek/uvtools/UVtoolsCmd convert'
                        command = f"{prusa_cmd} {pt_name} '{chunck_joined}' && {uvtools_cmd} {pt_name} pm3"
                        # self.slice(client=client, command=command)

                    if platform == 'darwin':
                        pt_dir = f'/Volumes/mediaserver/patients/{patient[0]} {patient[1]} {patient[2]}/'
                    else:
                        pt_dir = f'Z:\\patients\\{patient[0]} {patient[1]} {patient[2]}\\'

                    
                    link = self.get_nc_link(patient)
                    self.print_pt(patient, len(selected_files)/2, link)

            
            elif event.button.id == 'toggle-all':
                self.selectionlist.toggle_all()

            elif event.button.id == "exit":
                self.app.pop_screen()
        
        except Exception as e:
            self.log_error(str(e))


    def connect_to_server(self):
        client = paramiko.SSHClient()
        policy = paramiko.AutoAddPolicy()
        client.set_missing_host_key_policy(policy)
        client.connect(host, username=special_account, password=ubuntu_pass)
        return client
    

    @work(exclusive=False)
    def slice(self, client, command):
        try:
            stdin, stdout, stderr = client.exec_command(command, get_pty=True)
            self.query_one('#textlog').write(f'[bold teal]executing {command}')
            for line in iter(stdout.readline, ""):
                match = re.finditer(r'\d+(\.\d+)?%', line)
                self.app.call_from_thread(self.query_one('#textlog').write ,line)
                # self.query_one('#textlog').write(line)
                if match:
                    for pr in match:
                        progress = round(float(pr.group()[0:-1]))
                        self.app.call_from_thread(self.update_progress ,progress)
            client.close()
        except Exception as e:
            self.log_error(str(e))


    def print_pt(self, patient, nb_models, link):
        with open(f'C://Users//tarek//OneDrive//Documents//bt//{patient[0]}.txt', 'w') as pt_file:
            pt_file.write('ptID,ptFName,ptLName,UL,nbModels' + '\n')
            pt_file.write(f'{patient[0]},{patient[1]},{patient[2]},Lower,{nb_models}')

        with open(f'C://Users//tarek//OneDrive//Documents//bt//{patient[0]}2.txt', 'w') as pt_file:
            pt_file.write('ptID,ptFName,ptLName,UL,nbModels' + '\n')
            pt_file.write(f'{patient[0]},{patient[1]},{patient[2]},Upper,{nb_models}')

        with open(f'C://Users//tarek//OneDrive//Documents//bt2//{patient[0]}.txt', 'w') as pt_file:
            pt_file.write('ptFName,ptLName,link' + '\n')
            pt_file.write(f'{patient[1]},{patient[2]},{link}')




    def get_nc_link(self, patient):
        base = 'https://onyxceph.tarekserver.me/'
        root_path = f'Z://onyx-animation//clients//Client0//{patient[0]}'
        for dirpath, _, file in os.walk(root_path):
            for f in file:
                if f.endswith('.iiwgl'):
                    url = f'{base}?mlink={base}clients/Client0/{patient[0]}/{f}&fg=fff&bg=088&p=pms'
                    self.log_feedback(url)
                    return url
          
    
    def update_progress(self, progress):
        self.query_one('#progress').update(progress=progress)


    def log_feedback(self, msg):
        self.query_one('#feedback_popup').update(f'[bold #11696b]{str(msg)}')

    def log_error(self, msg):
        self.query_one('#feedback_popup').update(f'[bold red]{str(msg)}')



# Calendar Screen --------------------------------------------------------------------------------------------------------------------------------------------------
class Calendar(Screen):
    BINDINGS = [("ctrl+left", "previous_week", "Previous Week"),
            ("ctrl+right", "next_week", "Next Week"),
            ("f1", "add_encounter", "Add Encounter"),
            ("f2", "modify_patient", "Modify Patient"),
            ("ctrl+delete", "delete_encounter", "Delete Encounter"),
            ("f5", "clear_inputs", "Clear"),
            ("f10", "request_export", "Export")]
    week_index = reactive(0)
    row_index_id = {}
    row_index_enc_id = {}
    modify_pt = False

    def compose(self):
        self.table = DataTable()
        self.calendar_widget = DataTable(id='cal_table', fixed_columns=1, zebra_stripes=True)
        self.encounter_widget = DataTable(id='enc_table', zebra_stripes=True, fixed_columns=1)
        self.patient_widget = DataTable(id='pt_table', zebra_stripes=True, fixed_columns=1)
        self.patient_widget.cursor_type = 'row'

        self.inputs_container = Vertical(Horizontal(
                                    Input('', placeholder='First Name', id='fname'),Input('', placeholder='Last Name', id='lname'),
                                    Input('', placeholder='Date Of Birth', id='dob'), Input('', placeholder='Phone', id='phone'),
                                    Button('Add', id='addpatient'),Button('Update', id='updatepatient'), id='inputs'),
                                id='upper_cnt')
        self.tables_container = Vertical(
                            Horizontal(
                                Vertical(self.patient_widget,
                                        self.encounter_widget,
                                        Input(placeholder='Notes...', id='notes'), 
                                        TextLog(id='feedback', highlight=True, markup=True),
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
            await asyncio.sleep(10)  # Update every 10 seconds
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
        self.show_patients()
        self.show_encounters()


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
        if event.input.id != 'notes':
            try:
                fname = self.query_one('#fname').value
                lname = self.query_one('#lname').value
                phone = self.query_one('#phone').value
                if phone.isdigit():
                    phone = int(phone)
                else:
                    self.query_one('#phone').value = ''

                patients = conf.select_all_starts_with(first_name=fname, last_name=lname, phone=phone)
                if len(patients) != 0:
                    patient_id = patients[0][0]
                    row_index = self.row_index_id.get(patient_id)
                    self.patient_widget.move_cursor(row=row_index)
                    self.show_encounters()

            except Exception as e:
                self.log_error(e)


    def action_clear_inputs(self):
        for input in self.query(Input):
            input.value = ''


    def on_button_pressed(self, event: Button.Pressed):
        try:
            cursor = self.patient_widget.cursor_coordinate
            patient_id = self.patient_widget.get_cell_at(Coordinate(cursor.row, 0))
        except Exception as e:
            self.log_error("Error occurred while fetching patient ID: " + str(e))
            return

        try:
            first_name = self.query_one('#fname').value.capitalize()
            last_name = self.query_one('#lname').value.capitalize()
            phone = self.query_one('#phone').value
            date_of_birth = self.query_one('#dob').value
        except Exception as e:
            self.log_error("Error occurred while fetching input values: " + str(e))
            return

        # Validate the input values
        if not first_name or not last_name or not phone or not date_of_birth:
            self.log_error("Please fill in all fields.")
            return

        try:
            parsed_dob = parser.parse(date_of_birth).date()
        except ValueError:
            self.log_error("Invalid date format. Please use YYYY-MM-DD format.")
            return

        try:
            parsed_phone = int(phone)
        except ValueError:
            self.log_error("Invalid phone number. Please enter a valid integer.")
            return

        # Check for patient duplication
        try:
            existing_patient = conf.select_patient_by_details(first_name, last_name, parsed_phone, parsed_dob)
            if existing_patient:
                self.log_error("Patient with the same details already exists.")
                return
        except Exception as e:
            self.log_error("Error occurred while checking for existing patient: " + str(e))
            return

        try:
            if event.control.id == 'addpatient':
                self.add_patient(first_name, last_name, parsed_phone, parsed_dob)
            elif event.control.id == 'updatepatient':
                self.update_patient(patient_id, first_name, last_name, parsed_phone, parsed_dob)
            else:
                self.log_error("Invalid button event.")
                return
        except Exception as e:
            self.log_error("Error occurred while performing patient action: " + str(e))
            return


    def action_delete_encounter(self):
        try:
            cursor = self.calendar_widget.cursor_coordinate
            patient_name = self.calendar_widget.get_cell_at(cursor)
            if '_' in patient_name:
                self.log_error('No encounter to delete!')
                return
            
            encounter_time = self.get_datetime_from_cell(self.week_index, cursor.row, cursor.column)
            encounter_id = conf.select_encounter_by_rdv(encounter_time).encounter_id
            conf.delete_encounter(encounter_id)
            self.calendar_widget.update_cell_at(cursor, '_')
            self.encounter_widget.clear()
            self.log_feedback('Encounter deleted successfully.')
        except Exception as e:
            self.log_error("Error occurred on delete_encounter: " + str(e))


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
            # self.show_encounters(patient_id)
            self.log_feedback('Encounter added successfully')
            self.show_calendar(self.week_index)
            self.show_encounters()
            self.selected_calendar()
        except Exception as e:
            self.log_error(f"Error adding encounter: {e}")


    def get_datetime_from_cell(self,week_index, row, column):
        try:
            today = date.today()
            days_to_saturday = (today.weekday() - 5) % 7
            start_date = today - timedelta(days=days_to_saturday) + timedelta(weeks=week_index)
            day = start_date + timedelta(days=column - 1)
            time_slot_start, _ = conf.generate_time_slot(9, 0, 20, 21)[row]
            return dt.datetime.combine(day, time_slot_start)
        
        except Exception as e:
            self.log_error(f"Error in get_datetime_from_cell: {e}")


    def action_modify_patient(self):
        try:
            cursor = self.patient_widget.cursor_coordinate
            # patient_id = self.patient_widget.get_cell_at(Coordinate(cursor.row, 0))
            inputs = ['fname', 'lname', 'dob', 'phone']
            self.query_one('#fname').focus()

            if self.modify_pt == False:

                for i, inp in enumerate(inputs):
                    self.query_one(f'#{inp}').value = self.patient_widget.get_cell_at(Coordinate(cursor.row, i+1))
                    self.query_one(f'#{inp}').styles.background = 'teal'
                    if i==4:
                        self.query_one(f'#{inp}').value = int(self.patient_widget.get_cell_at(Coordinate(cursor.row, i+1)))
                self.modify_pt = True
                pass

            else :
                for i, inp in enumerate(inputs):
                    self.query_one(f'#{inp}').value = ''
                    self.query_one(f'#{inp}').styles.background = self.styles.background
                self.modify_pt = False
        except Exception as e:
            self.log_error(f"Error in modify_patient: {e}")
            


    def add_patient(self, first_name, last_name, phone, date_of_birth):
        try:
            patient = conf.Patient(first_name=first_name, last_name=last_name, phone=phone, date_of_birth=date_of_birth)
            patient_id = conf.save_to_db(patient)
            self.log_feedback("Patient added successfully.")
            self.show_patients()
            self.calendar_widget.move_cursor(row=0, column=0)
            row_index = self.row_index_id.get(str(patient_id))
            self.patient_widget.move_cursor(row=row_index)
            foldername = f"Z:\\patients\\{patient_id} {patient.first_name} {patient.last_name}"
            isExist = os.path.exists(f'Z:\\patients\\{foldername}')
            self.show_encounters()
            if not isExist:
                os.makedirs(foldername)

        except Exception as e:
            self.log_error(f"Error adding patient: {e}")


    def update_patient(self, patient_id, first_name, last_name, phone, date_of_birth):
        try:
            self.action_modify_patient()
            old_patient = conf.select_patient_by_id(patient_id)
            conf.update_patient(patient_id=patient_id, first_name=first_name, last_name=last_name, phone=phone, date_of_birth=date_of_birth)
            self.log_feedback("Patient updated successfully.")
            self.show_patients()
            row_index = self.row_index_id.get(str(patient_id))
            self.patient_widget.move_cursor(row=row_index)

            old_foldername = f"Z:\\patients\\{patient_id} {old_patient.first_name} {old_patient.last_name}"
            new_foldername = f"Z:\\patients\\{patient_id} {first_name} {last_name}"
            isExist = os.path.exists(f'Z:\\patients\\{new_foldername}')
            if not isExist:
                os.rename(old_foldername, new_foldername)


        except Exception as e:
            self.log_error(f"Error updating patient: {e}")


    def log_error(self, msg):
        timestamp = dt.datetime.now()
        self.query_one('#feedback').write(f'{timestamp}---[bold red]{str(msg)}')

    def action_next_week(self):
        self.week_index += 1 
        self.show_calendar(self.week_index)

    def action_previous_week(self):
        self.week_index -= 1 
        self.show_calendar(self.week_index)

    def log_feedback(self, msg):
        timestamp = dt.datetime.now()
        self.query_one('#feedback').write(f'{timestamp}---[bold #11696b]{str(msg)}')


    def show_patients(self):
        try:
            self.patient_widget.clear()
            patients = iter(conf.select_all_starts_with())
            self.row_index_id = {}
            for index, patient in enumerate(patients):
                patient_id = patient[0]
                self.patient_widget.add_row(*patient, key=patient_id)
                self.row_index_id.update({patient_id: index})
                # self.log_feedback()
        except Exception as e:
            self.log_error("Error occurred in show_patients: " + str(e))


    def show_encounters(self):
        try:
            if self.patient_widget.row_count == 0:
                return

            self.encounter_widget.clear()
            pt_id = int(self.patient_widget.get_row_at(self.patient_widget.cursor_row)[0])
            # self.log_feedback(pt_id)
            encounters = iter(conf.select_all_pt_encounters(pt_id))
            for index, row in enumerate(encounters):
                encounter_id = row[0]
                self.encounter_widget.add_row(*row, height=int(len(row[2]) / 20 + 1))
                self.row_index_enc_id.update({encounter_id: index})
        except Exception as e:
            self.log_error("Error occurred in show_encounters: " + str(e))


    def show_calendar(self, week_index):
        try:
            current_row = self.calendar_widget.cursor_row
            current_column = self.calendar_widget.cursor_column

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

            self.calendar_widget.move_cursor(row=current_row, column=current_column, animate=True)
            self.selected_calendar()
        except Exception as e:
            self.log_error("Error occurred in show_calendar: " + str(e))



    def on_data_table_cell_selected(self, message: DataTable.CellSelected):
        try:
            if message.control.id == 'enc_table':
                self.query_one('#notes').focus()
                self.query_one('#notes').value = ''
            if message.control.id == 'cal_table':
                self.selected_calendar()
                self.selected_calendar()
                # self.update_tooltip()
        except Exception as e:
            self.log_error(e)


    # def on_data_table_cell_highlighted(self, message: DataTable.CellHighlighted):
    #     if message.control.id == 'cal_table':
    #         self.update_tooltip()

        
    def selected_calendar(self):
        try:
            cursor = self.calendar_widget.cursor_coordinate
            cursor_value = self.calendar_widget.get_cell_at(cursor)
            if '_' in cursor_value or ':' in cursor_value:
            #     # self.show_patients()
            #     # self.encounter_widget.clear()
                return
        
            # start = tm.time()
            encounter_time = self.get_datetime_from_cell(self.week_index, cursor.row, cursor.column)
            encounter = conf.select_encounter_by_rdv(encounter_time)
            patient_id = encounter.patient_id
            encounter_id = encounter.encounter_id

            row_index = self.row_index_id.get(str(patient_id))
            row_index_enc = self.row_index_enc_id.get(str(encounter_id))
            self.patient_widget.move_cursor(row=row_index, animate=True)
            self.show_encounters()

            # start = tm.time()
            cursor_enc = self.encounter_widget.cursor_coordinate
            self.encounter_widget.cursor_type = 'row'
            self.encounter_widget.move_cursor(row=row_index_enc, column=cursor_enc.column)
            end = tm.time()

            # self.log_feedback(end-start)

        except Exception as e:
            self.log_error(e)


    def on_data_table_row_selected(self, message: DataTable.RowSelected):
        try:
            if message.control.id == 'pt_table':
                if self.modify_pt == True:
                    self.action_modify_patient()
                self.encounter_widget.cursor_type = 'row'
                cursor = self.calendar_widget.cursor_coordinate
                cursor_value = self.calendar_widget.get_cell_at(cursor)
                if '_' not in cursor_value:
                    self.calendar_widget.move_cursor(row=0, column=0)
                self.show_encounters()
            elif message.control.id == 'enc_table':
                self.encounter_widget.cursor_type = 'cell'
                self.calendar_widget.move_cursor(row=0, column=0)
        except Exception as e:
            self.log_error(e)
            

    
# ------------------------------------------------------------------------Main App-----------------------------------------------------------------------------------------
class PMSApp(App):
    BINDINGS = [("ctrl+left", "previous_week", "Previous Week"),
            ("ctrl+right", "next_week", "Next Week"),
            ("f1", "add_encounter", "Add Encounter"),
            ("f2", "modify_patient", "Modify Patient"),
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
        self.push_screen(PrintExportScreen())

if __name__ == "__main__":
    app = PMSApp()
    app.run()

 
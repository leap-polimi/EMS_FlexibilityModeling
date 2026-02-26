# -*- coding: utf-8 -*-
"""
Energy Management System (EMS) - reporting module
Copyright (C) 2020-2024 LEAP scarl
Authors:
- Matteo Zatti
- Marco Gabba
- Filippo Bovera

Modifications in this fork are authored by:
- Andrea Scrocca
- Filippo Bovera
Affiliation: Politecnico di Milano, Department of Energy

This file is part of EMS

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import cloudpickle as pickle
import pandas as pd
import os

import src.CIRCUIT as circuit_lib

def save_results(b, name, folder):
    import pandas as pd
    
    #Create dataframe with time-indexed variables
    
    time_indexed = pd.DataFrame()
    time_indexed['Index'] = [t for t in b.TIME_s]
    time_indexed.set_index("Index", inplace=True)
    
    # Create series with static variables
    static = pd.DataFrame()
    
    static['OPEX'] = [b.OPEX.value]
    static['penalty_withdrawn_v'] = [b.penalty_withdrawn_v.value]
    static['penalty_slack_v'] = [b.penalty_slack_v.value]
    static['penalty_imbalance_v'] = [b.penalty_imbalance_v.value]
    static['cost_electricity_v'] = [sum(b.model().POD_b[p].cost_electricity_v.value for p in b.POD_s)]
    static['revenue_electricity_v'] = [sum(b.model().POD_b[p].revenue_electricity_v.value for p in b.POD_s)]
    static['cost_gas_v'] = [sum(b.model().PDR_b[p].cost_total_v.value for p in b.PDR_s)]
    static['costO&M_Genset_v'] = [sum(b.model().GENSET_b[g].cost_operationMaintenance_v.value for g in b.GENSET_s)]
    static['costO&M_BESS_v'] = [sum(b.model().BESS_b[e].cost_operationMaintenance_v.value for e in b.BESS_s)]
    static['costO&M_COGEN_v'] = [sum(b.model().COGEN_b[g].cost_operationMaintenance_v.value for g in b.COGEN_s)]
    static['costO&M_BOILER_v'] = [sum(b.model().BOILER_b[g].cost_operationMaintenance_v.value for g in b.BOILER_s)]
    static['revenue_FLEX_v'] = [sum(b.model().FLEX_b[q].revenue_flexUp_v.value + b.model().FLEX_b[q].revenue_flexDown_v.value for q in b.FLEX_s)]
    
    return (time_indexed, static)

TEST_FOLDER = 'examples'
TEST_SELECTION  = '0_rescheduling_FLEX'
draw_graphs=True
print_report=True

FILE_PATH = './'+TEST_FOLDER+'/'+TEST_SELECTION

if not os.path.exists(FILE_PATH+'/reports'):
    os.makedirs(FILE_PATH+'/reports')

instance = pickle.load(open(FILE_PATH+'/solution.pkl', "rb"))

#Create Excel file to store results

if print_report:
    writer = pd.ExcelWriter(FILE_PATH+'/results.xlsx',engine='openpyxl')   
    workbook=writer.book
    
    general_time, general_static = save_results(instance,'GENERAL',FILE_PATH)
    general_time.to_excel(writer,sheet_name='GENERAL_timeindexed',startrow=0 , startcol=0)   
    general_static.to_excel(writer,sheet_name='GENERAL_static',startrow=0 , startcol=0)  

for u in instance.EL_CIRCUIT_s:
    if draw_graphs: 
        circuit_lib.create_reportEL(instance.EL_CIRCUIT_b[u],u,FILE_PATH)
    if print_report:
        el_circuit_time, el_circuit_static = circuit_lib.el_save_results(instance.EL_CIRCUIT_b[u],u,FILE_PATH)
        el_circuit_time.to_excel(writer,sheet_name=f'{u}_timeindexed',startrow=0 , startcol=0)   
        el_circuit_static.to_excel(writer,sheet_name=f'{u}_static',startrow=0 , startcol=0) 
    
for u in instance.TH_CIRCUIT_s:
    if draw_graphs:
        circuit_lib.create_reportTH(instance.TH_CIRCUIT_b[u],u,FILE_PATH)  
        
    if print_report:
        th_circuit_time, th_circuit_static = circuit_lib.th_save_results(instance.TH_CIRCUIT_b[u],u,FILE_PATH)
        th_circuit_time.to_excel(writer,sheet_name=f'{u}_timeindexed',startrow=0 , startcol=0)   
        th_circuit_static.to_excel(writer,sheet_name=f'{u}_static',startrow=0 , startcol=0) 
    
for u in instance.NG_CIRCUIT_s:
    if draw_graphs:
        circuit_lib.create_reportNG(instance.NG_CIRCUIT_b[u],u,FILE_PATH) 
    
    if print_report:
        ng_circuit_time, ng_circuit_static = circuit_lib.ng_save_results(instance.NG_CIRCUIT_b[u],u,FILE_PATH)
        ng_circuit_time.to_excel(writer,sheet_name=f'{u}_timeindexed',startrow=0 , startcol=0)   
        ng_circuit_static.to_excel(writer,sheet_name=f'{u}_static',startrow=0 , startcol=0) 

for u in instance.FLEX_s:
    if draw_graphs:
        circuit_lib.create_reportFLEX(instance.FLEX_b[u],u,FILE_PATH) 
    
    if print_report:
        flex_circuit_time, flex_circuit_static = circuit_lib.flex_save_results(instance.FLEX_b[u],u,FILE_PATH)
        flex_circuit_time.to_excel(writer,sheet_name=f'{u}_timeindexed',startrow=0 , startcol=0)   
        flex_circuit_static.to_excel(writer,sheet_name=f'{u}_static',startrow=0 , startcol=0) 
  
if print_report:
    writer.close()






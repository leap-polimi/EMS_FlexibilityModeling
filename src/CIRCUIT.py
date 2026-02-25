# -*- coding: utf-8 -*-
"""
Energy Management System (EMS) - CIRCUITs reporting routines
Copyright (C) 2020-2024 LEAP scarl
Authors:
- Matteo Zatti
- Marco Gabba
- Filippo Bovera

Further development / modifications (fork):
Copyright (C) 2024-2026 Andrea Scrocca and Filippo Bovera
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
from pyomo.core import AbstractModel,Set,RangeSet,Param,Var,Constraint, Objective, minimize, NonNegativeIntegers,NonNegativeReals,Binary, Block
import pyomo.environ as pyo
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import pandas as pd
import pathlib, webbrowser

def create_reportEL(b,name,folder):   
    b.TIME_s = Set(initialize=b.model().TIME_s)  
    b.mode_p = Param(initialize=b.model().logic_schedulingReschedulingSelection_p)
    xrange = [b.TIME_s.first(),b.TIME_s.last()]
    xticks = list(range(1,b.model().timesteps_p.value,int(1/b.model().timestep_size_p.value)))
    xtext = list(range(0,(int(b.model().timesteps_p.value*b.model().timestep_size_p.value))))
    
    fig = make_subplots(
        rows=2, cols=1,  # Two rows, one column
        row_heights=[0.75, 0.25],
        shared_xaxes=True,  # Share the x-axis
        vertical_spacing=0.1,  # Space between subplots
        subplot_titles=("Electricity Balance", "BESS SOC")
    )

    time = [t for t in b.TIME_s]
#Output of electricity Balance - LOAD + POD (injected)  + BESS ( for charging )     
    for l in b.CONNECTED_EL_LOAD_s:
        EL_OUT= [pyo.value(b.model().EL_LOAD_b[l].power_electricityDemand_p[t]) for t in b.TIME_s]
        fig.add_trace(go.Scatter(
            x = time,
            y = EL_OUT,
            name = f'Electric Load - {l} [kW]',
            opacity = .5,
            hovertext= ['Value: {:.2f}'.format(val) for val in EL_OUT]),
            row=1,
            col=1) 
    
    my_base = [0 for t in b.TIME_s]        

        
    for p in b.CONNECTED_POD_s:
        EL_OUT=[pyo.value(b.model().POD_b[p].power_electricityInjected_v[t]) for t in b.TIME_s]
        fig.add_trace(go.Bar(
            x = time,
            y = [-val for val in EL_OUT],
            base = my_base,
            name = f'POD Injected - {p} [kW]',
            opacity = .5,
            hovertext= ['Value: {:.2f}'.format(val) for val in EL_OUT],
            offsetgroup = 0),
            row=1,
            col=1)
        my_base = [my_base[t-1] - EL_OUT[t-1] for t in b.TIME_s]

    
        
    for e in b.CONNECTED_BESS_s:
        EL_OUT=[pyo.value(b.model().BESS_b[e].power_chargeAC_v[t]*b.model().BESS_b[e].power_nominal_p) for t in b.TIME_s]
        fig.add_trace(go.Bar(
            x = time,
            y = [-val for val in EL_OUT],
            base = my_base,
            name = f'BESS Charging - {e} [kW]',
            opacity = .5,
            hovertext= ['Value: {:.2f}'.format(val) for val in EL_OUT],
            offsetgroup = 0),
            row=1,
            col=1)
        my_base = [my_base[t-1] - EL_OUT[t-1] for t in b.TIME_s]

        EL_OUT=[pyo.value(b.model().BESS_b[e].power_aux_v[t]) for t in b.TIME_s]
        fig.add_trace(go.Bar(
            x = time,
            y = [-val for val in EL_OUT],
            base = my_base,
            name = f'BESS Auxiliaries - {e} [kW]',
            opacity = .5,
            hovertext= ['Value: {:.2f}'.format(val) for val in EL_OUT],
            offsetgroup = 0),
            row=1,
            col=1)
        my_base = [my_base[t-1] - EL_OUT[t-1] for t in b.TIME_s]
      
    for v in b.CONNECTED_EV_s:
        EL_OUT=[pyo.value(b.model().EV_b[v].power_Charged_v[t]) for t in b.TIME_s]
        fig.add_trace(go.Bar(
            x = time,
            y = [-val for val in EL_OUT],
            base = my_base,
            name = f'EV Charging - {v} [kW]',
            opacity = .5,
            hovertext= ['Value: {:.2f}'.format(val) for val in EL_OUT],
            offsetgroup = 0),
            row=1,
            col=1)
        my_base = [my_base[t-1] - EL_OUT[t-1] for t in b.TIME_s]
 
#Input of electricity Balance - Each GENSET + COGEN + BESS ( DISCHARGED )+  PV + POD (WITHDRAWN)
    my_base = [0 for t in b.TIME_s]     
    for p in b.CONNECTED_POD_s:
        EL_IN=[pyo.value(b.model().POD_b[p].power_electricityWithdrawn_v[t]) for t in b.TIME_s]
        fig.add_trace(go.Bar(
            x = time,
            y = EL_IN,
            base = my_base,
            name = f'POD Withdrawn - {p} [kW]',
            opacity = .5,
            hovertext= ['Value: {:.2f}'.format(val) for val in EL_IN],
            offsetgroup = 1),
            row=1,
            col=1)
        my_base = [my_base[t-1] + EL_IN[t-1] for t in b.TIME_s]
        
    for p in b.CONNECTED_PV_s:
        EL_IN=[pyo.value(b.model().PV_b[p].power_electricityProduction_p[t]) for t in b.TIME_s]
        fig.add_trace(go.Bar(
            x = time,
            y = EL_IN,
            base = my_base,
            name = f'PV production - {p} [kW]',
            opacity = .5,
            hovertext= ['Value: {:.2f}'.format(val) for val in EL_IN],
            offsetgroup = 1),
            row=1,
            col=1)
        my_base = [my_base[t-1] + EL_IN[t-1] for t in b.TIME_s]  
        
    for g in b.CONNECTED_COGEN_s:
        EL_IN=[pyo.value(b.model().COGEN_b[g].power_electricityOutput_v[t]) for t in b.TIME_s]
        fig.add_trace(go.Bar(
            x = time,
            y = EL_IN,
            base = my_base,
            name = f'Cogen production - {g} [kW]',
            opacity = .5,
            hovertext= ['Value: {:.2f}'.format(val) for val in EL_IN],
            offsetgroup = 1),
            row=1,
            col=1)
        my_base = [my_base[t-1] + EL_IN[t-1] for t in b.TIME_s] 
        
    for g in b.CONNECTED_GENSET_s:
        EL_IN=[pyo.value(b.model().GENSET_b[g].power_electricityOutput_v[t]) for t in b.TIME_s]
        fig.add_trace(go.Bar(
            x = time,
            y = EL_IN,
            base = my_base,
            name = f'Genset production - {g} [kW]',
            opacity = .5,
            hovertext= ['Value: {:.2f}'.format(val) for val in EL_IN],
            offsetgroup = 1),
            row=1,
            col=1)
        my_base = [my_base[t-1] + EL_IN[t-1] for t in b.TIME_s]        
 

                
    for e in b.CONNECTED_BESS_s:
       EL_IN=[pyo.value(b.model().BESS_b[e].power_dischargeAC_v[t]*b.model().BESS_b[e].power_nominal_p) for t in b.TIME_s]
       fig.add_trace(go.Bar(
           x = time,
           y = EL_IN,
           base = my_base,
           name = f'BESS discharging - {e} [kW]',
           opacity = .5,
           hovertext= ['Value: {:.2f}'.format(val) for val in EL_IN],
           offsetgroup = 1),
           row=1,
           col=1)
       my_base = [my_base[t-1] + EL_IN[t-1] for t in b.TIME_s]
       

    if b.model().logic_schedulingReschedulingSelection_p==1 and b.model().logic_rescheduling_localGlobalSelection_p==1:       
        for p in b.CONNECTED_POD_s:
            EL_IN=[pyo.value(b.model().POD_b[p].BDE_Down_v[t]) for t in b.TIME_s]
            fig.add_trace(go.Scatter(
                x = time,
                y = EL_IN,
                line= dict(color='red', width=3, dash='solid'),
                name = f'BDE Down - {p} [kW]',
                opacity = .5,
                hovertext= ['Value: {:.2f}'.format(val) for val in EL_IN]
                ),
                row=1,
                col=1)
        
        for p in b.CONNECTED_POD_s:
            EL_OUT=[pyo.value(b.model().POD_b[p].baselineWithdrawn_p[t]-b.model().POD_b[p].baselineInjected_p[t]) for t in b.TIME_s]
            fig.add_trace(go.Scatter(
                x = time,
                y = EL_OUT,
                line= dict(color='black', width=3, dash='solid'),
                name = f'Baseline- {p} [kW]',
                opacity = .5,
                hovertext= ['Value: {:.2f}'.format(val) for val in EL_OUT]
                ),
                row=1,
                col=1)       
        for p in b.CONNECTED_POD_s:
            EL_OUT=[pyo.value(b.model().POD_b[p].BDE_Up_v[t]) for t in b.TIME_s]
            fig.add_trace(go.Scatter(
                x = time,
                y = [-val for val in EL_OUT],
                line= dict(color='green', width=3, dash='solid'),
                name = f'BDE Up- {p} [kW]',
                opacity = .5,
                hovertext= ['Value: {:.2f}'.format(val) for val in EL_OUT]
                ),
                row=1,
                col=1)
            
    #Add traces for BESS SOC in the second subplot
    for e in b.model().BESS_s:
        BESS_SOC=[pyo.value(b.model().BESS_b[e].energy_soc_v[t]*100) for t in b.model().TIME_s]
        fig.add_trace(go.Scatter(
            x = time,
            y = BESS_SOC,
            name = f'BESS SOC - {e} [%]',
            opacity = .5,
            hovertext= ['Value: {:.2f}'.format(val) for val in BESS_SOC]),
            row=2,
            col=1)
        
    fig.update_layout(height=500, title_text=f'Electricity Balance - {name}',title_x=0.5, showlegend=True,
                      template="plotly_white",
                      barmode="stack",
                      xaxis1 = dict(range=xrange, tickvals=xticks, ticktext=xtext),
                      hovermode="x unified"
                      )      
    address = f'{folder}/Reports/{name}.html'
    uri = pathlib.Path(address).absolute().as_uri()
    
    with open(address, 'w') as f:
        f.write(fig.to_html(full_html=True, include_plotlyjs='cdn'))
       
    uri = pathlib.Path(address).absolute().as_uri()
    webbrowser.open(uri)    
    
def create_reportTH(b,name,folder):    
    b.TIME_s = Set(initialize=b.model().TIME_s)  
    
    xrange = [b.TIME_s.first(),b.TIME_s.last()]
    xticks = list(range(1,b.model().timesteps_p.value,int(1/b.model().timestep_size_p.value)))
    xtext = list(range(0,(int(b.model().timesteps_p.value*b.model().timestep_size_p.value))))
    
    fig = make_subplots(
        rows=1, cols=1,
        shared_yaxes=True
        )
    
    time = [t for t in b.TIME_s]
#Output of Thermal Balance - LOAD     
    
    for l in b.CONNECTED_TH_LOAD_s:
        TH_OUT= [pyo.value(b.model().TH_LOAD_b[l].power_heatDemand_p[t]) for t in b.TIME_s]
        fig.add_trace(go.Scatter(
            x = time,
            y = TH_OUT,
            name = f'Thermal Load - {l} [kW]',
            opacity = .5,
            hovertext= ['Value: {:.2f}'.format(val) for val in TH_OUT],))  
    


#Input of Thermal Balance - Each BOILER + COGEN 
    my_base = [0 for t in b.TIME_s]  
    for g in b.CONNECTED_COGEN_s:
        TH_IN=[pyo.value(b.model().COGEN_b[g].power_heatOutput_v[t]) for t in b.TIME_s]
        fig.add_trace(go.Bar(
            x = time,
            y = TH_IN,
            base = my_base,
            name = f'Cogen production - {g} [kW]',
            opacity = .5,
            hovertext= ['Value: {:.2f}'.format(val) for val in TH_IN],
            offsetgroup = 1))
        my_base = [my_base[t-1] + TH_IN[t-1] for t in b.TIME_s]
        
    for u in b.CONNECTED_BOILER_s:
        TH_IN=[pyo.value(b.model().BOILER_b[u].power_heatOutput_v[t]) for t in b.TIME_s]
        fig.add_trace(go.Bar(
            x = time,
            y = TH_IN,
            base = my_base,
            name = f'BOILER Production - {u} [kW]',
            opacity = .5,
            hovertext= ['Value: {:.2f}'.format(val) for val in TH_IN],
            offsetgroup = 1))
        my_base = [my_base[t-1] + TH_IN[t-1] for t in b.TIME_s]

 

        
        
    fig.update_layout(height=500, title_text=f'Thermal Balance - {name}',title_x=0.5, showlegend=True,
                      template="plotly_white",
                      barmode="stack",
                      xaxis1 = dict(range=xrange, tickvals=xticks, ticktext=xtext),
                      hovermode="x unified"
                      )      
  
    address = f'{folder}/Reports/{name}.html'
    uri = pathlib.Path(address).absolute().as_uri()
    
    with open(address, 'w') as f:
        f.write(fig.to_html(full_html=True, include_plotlyjs='cdn'))
       
    uri = pathlib.Path(address).absolute().as_uri()
    webbrowser.open(uri) 

    
def create_reportNG(b,name,folder):    
    b.TIME_s = Set(initialize=b.model().TIME_s)  
    
    xrange = [b.TIME_s.first(),b.TIME_s.last()]
    xticks = list(range(1,b.model().timesteps_p.value,int(1/b.model().timestep_size_p.value)))
    xtext = list(range(0,(int(b.model().timesteps_p.value*b.model().timestep_size_p.value))))
    
    fig = make_subplots(
        rows=1, cols=1,
        shared_yaxes=True
        )
    time = [t for t in b.TIME_s]
#Output of natural gas Balance - GAS WITHDRAWN FROM PDR     
    for u in b.CONNECTED_PDR_s:
        NG_OUT= [pyo.value(b.model().PDR_b[u].smc_withdrawn_v[t]*b.model().PDR_b[u].LHV_p/b.model().timestep_size_p) for t in b.TIME_s]
        fig.add_trace(go.Scatter(
            x = time,
            y = NG_OUT,
            name = f'Natural Gas withdrawn - {u} [kW fuel ]',
            opacity = .5,
            hovertext= ['Value: {:.2f}'.format(val) for val in NG_OUT],)) 

#Input of Natural GAS Balance - Each GENSET + COGEN + BOILER

    my_base = [0 for t in b.TIME_s]   
     
    for g in b.CONNECTED_COGEN_s:
        NG_IN=[pyo.value(b.model().COGEN_b[g].power_fuelInput_v[t]) for t in b.TIME_s]
        fig.add_trace(go.Bar(
            x = time,
            y = NG_IN,
            base = my_base,
            name = f'Cogen Power fuel input - {g} [kW fuel]',
            opacity = .5,
            hovertext= ['Value: {:.2f}'.format(val) for val in NG_IN],
            offsetgroup = 1))
        my_base = [my_base[t-1] + NG_IN[t-1] for t in b.TIME_s]  
    
    for g in b.CONNECTED_GENSET_s:
        NG_IN=[pyo.value(b.model().GENSET_b[g].power_fuelInput_v[t]) for t in b.TIME_s]
        fig.add_trace(go.Bar(
            x = time,
            y = NG_IN,
            base = my_base,
            name = f'Genset Power fuel input- {g} [kW fuel]',
            opacity = .5,
            hovertext= ['Value: {:.2f}'.format(val) for val in NG_IN],
            offsetgroup = 1))
        my_base = [my_base[t-1] + NG_IN[t-1] for t in b.TIME_s]

   

    for u in b.CONNECTED_BOILER_s:
        NG_IN=[pyo.value(b.model().BOILER_b[u].power_fuelInput_v[t]) for t in b.TIME_s]
        fig.add_trace(go.Bar(
            x = time,
            y = NG_IN,
            base = my_base,
            name = f'BOILER Power fuel input - {u} [kW fuel]',
            opacity = .5,
            hovertext= ['Value: {:.2f}'.format(val) for val in NG_IN],
            offsetgroup = 1))
        my_base = [my_base[t-1] + NG_IN[t-1] for t in b.TIME_s]

    fig.update_layout(height=500, title_text=f'Natural Gas Balance - {name}',title_x=0.5, showlegend=True,
                      template="plotly_white",
                      barmode="stack",
                      xaxis1 = dict(range=xrange, tickvals=xticks, ticktext=xtext),
                      hovermode="x unified"
                      )        
 
    address = f'{folder}/Reports/{name}.html'
    uri = pathlib.Path(address).absolute().as_uri()
    
    with open(address, 'w') as f:
        f.write(fig.to_html(full_html=True, include_plotlyjs='cdn'))
       
    uri = pathlib.Path(address).absolute().as_uri()
    webbrowser.open(uri)

def create_reportFLEX(b,name,folder):   
    b.TIME_s = Set(initialize=b.model().TIME_s)  
    b.mode_p = Param(initialize=b.model().logic_schedulingReschedulingSelection_p)
    xrange = [b.TIME_s.first(),b.TIME_s.last()]
    xticks = list(range(1,b.model().timesteps_p.value,int(1/b.model().timestep_size_p.value)))
    xtext = list(range(0,(int(b.model().timesteps_p.value*b.model().timestep_size_p.value))))

    time = [t for t in b.TIME_s]

    # Safe numeric extraction: return 0 if a Var is uninitialized
    def _v(expr, default=0.0):
        val = pyo.value(expr, exception=False)
        return default if val is None else float(val)
    
    # Create subplots with a shared x-axis
    fig = make_subplots(
        rows=3, cols=1,  # Three rows, one column
        shared_xaxes=True,  # Share the x-axis
        vertical_spacing=0.1,  # Space between subplots
        subplot_titles=("Capacity Retention breakdown", "Baseline and real Exchange", "Dispatched vs Provided Flexibility")
    )

    if b.model().logic_schedulingReschedulingSelection_p==0 and b.model().FLEX_b["FLEX_1"].logic_is_capacityRetention_Optimized_p==1:
        FLEX_UP = [pyo.value(b.model().FLEX_b["FLEX_1"].power_flexUp_v[t]) for t in b.TIME_s]
        fig.add_trace(go.Scatter(
            x = time,
            y = FLEX_UP,
            name = f'Provided Upward Flexibility [kW]',
            opacity = .5,
            hovertext= ['Value: {:.2f}'.format(val) for val in FLEX_UP]),
            row=1,
            col=1) 
        
        POD=[pyo.value(b.model().FLEX_b["FLEX_1"].baseline_p[t])-pyo.value(b.model().POD_b["POD_1"].power_electricityWithdrawn_v[t]-b.model().POD_b["POD_1"].power_electricityInjected_v[t]) for t in b.TIME_s]
        fig.add_trace(go.Scatter(
            x = time,
            y = POD,
            name = f'(Baseline - Real_POD) [kW]',
            opacity = .5,
            hovertext= ['Value: {:.2f}'.format(val) for val in POD]),
            row=1,
            col=1)

        my_base = [0 for t in b.TIME_s]        

        for e in b.FLEX_BESS_s:
            BESS_CR=[pyo.value(b.model().BESS_b[e].power_capacityRetentionUp_v[t]) for t in b.TIME_s]
            fig.add_trace(go.Bar(
                x = time,
                y = BESS_CR,
                base = my_base,
                name = f'BESS CR [kW]',
                opacity = .5,
                hovertext= ['Value: {:.2f}'.format(val) for val in BESS_CR],
                offsetgroup = 0),
                row=1,
                col=1)
            my_base = [my_base[t-1] + BESS_CR[t-1] for t in b.TIME_s]
        
        for g in b.FLEX_COGEN_s:
            COGEN_CR=[pyo.value(b.model().COGEN_b[g].power_capacityRetentionUp_v[t]) for t in b.TIME_s]
            fig.add_trace(go.Bar(
                x = time,
                y = COGEN_CR,
                base = my_base,
                name = f'CHP CR [kW]',
                opacity = .5,
                hovertext= ['Value: {:.2f}'.format(val) for val in COGEN_CR],
                offsetgroup = 0),
                row=1,
                col=1)
            my_base = [my_base[t-1] + COGEN_CR[t-1] for t in b.TIME_s] 
        
        # Add a trace for the baseline in the second subplot
        baseline = [pyo.value(b.model().FLEX_b["FLEX_1"].baseline_p[t]) for t in b.TIME_s]
        fig.add_trace(go.Scatter(x=time, y=baseline, mode='lines+markers', name='Baseline [kW]', 
                            line=dict(color='steelblue')), row=2, col=1)
        
        # Add a trace for the real POD exchange in the second subplot
        real_POD = [pyo.value(b.model().POD_b["POD_1"].power_electricityWithdrawn_v[t]-b.model().POD_b["POD_1"].power_electricityInjected_v[t]) for t in b.TIME_s]
        fig.add_trace(go.Scatter(x=time, y=real_POD, mode='lines+markers', name='Real POD exchange [kW]', 
                            line=dict(color='firebrick')), row=2, col=1)
        
    if b.model().logic_schedulingReschedulingSelection_p==1 and b.model().logic_rescheduling_localGlobalSelection_p==0:
        #DIAGRAM 1
        FLEX_UP_SCH_96 = [pyo.value(b.model().FLEX_b["FLEX_1"].power_scheduled_capacityRetentionUp_p[t]) for t in b.TIME_s]
        fig.add_trace(go.Scatter(
            x = time,
            y = FLEX_UP_SCH_96,
            name = f'Reserved power [kW]',
            opacity = .5,
            hovertext= ['Value: {:.2f}'.format(val) for val in FLEX_UP_SCH_96]),
            row=1,
            col=1)
            
        my_base = [0 for t in b.TIME_s]      
            
        for e in b.FLEX_BESS_s:
            BESS_CR=[pyo.value(b.model().BESS_b[e].power_capacityRetentionUp_v[t]) for t in b.TIME_s]

            fig.add_trace(go.Bar(
                x = time,
                y = BESS_CR,
                base = my_base,
                name = f'BESS CR [kW]',
                opacity = .5,
                hovertext= ['Value: {:.2f}'.format(val) for val in BESS_CR],
                offsetgroup = 0),
                row=1,
                col=1)
            my_base = [my_base[t-1] + BESS_CR[t-1] for t in b.TIME_s]

        for g in b.FLEX_COGEN_s:
            COGEN_CR=[pyo.value(b.model().COGEN_b[g].power_capacityRetentionUp_v[t]) for t in b.TIME_s]
            fig.add_trace(go.Bar(
                x = time,
                y = COGEN_CR,
                base = my_base,
                name = f'CHP CR [kW]',
                opacity = .5,
                hovertext= ['Value: {:.2f}'.format(val) for val in COGEN_CR],
                offsetgroup = 0),
                row=1,
                col=1)
        
        #DIAGRAM 2
        FLEX_UP_BASELINE_96 = [pyo.value(b.model().FLEX_b["FLEX_1"].baseline_p[t]) for t in b.TIME_s]
        fig.add_trace(go.Scatter(
            x = time,
            y = FLEX_UP_BASELINE_96,
            name = f'Baseline [kW]',
            opacity = .5,
            hovertext= ['Value: {:.2f}'.format(val) for val in FLEX_UP_BASELINE_96]),
            row=2,
            col=1)
        
        my_base = [0 for t in b.TIME_s]  
        
        POD = [pyo.value(b.model().POD_b["POD_1"].power_electricityWithdrawn_v[t]-b.model().POD_b["POD_1"].power_electricityInjected_v[t]) for t in b.TIME_s]
        fig.add_trace(go.Bar(
            x = time,
            y = POD,
            base = my_base,
            name = f'POD [kW]',
            opacity = .5,
            hovertext= ['Value: {:.2f}'.format(val) for val in POD],
            offsetgroup = 0),
            row=2,
            col=1)
        
        my_base = [my_base[t-1] + POD[t-1] for t in b.TIME_s]
        
        FLEX_UP_ACT_96 = [pyo.value(b.model().FLEX_b["FLEX_1"].power_FlexActivatedUp_v[t]) for t in b.TIME_s]
        fig.add_trace(go.Bar(
            x = time,
            y = FLEX_UP_ACT_96,
            base = my_base,
            name = f'Provided Upward Flexibility [kW]',
            opacity = .5,
            hovertext= ['Value: {:.2f}'.format(val) for val in FLEX_UP_ACT_96],
            offsetgroup = 0),
            row=2,
            col=1)
        
        #3° DIAGRAM
        FLEX_UP_DIS_96 = [pyo.value(b.model().FLEX_b["FLEX_1"].local_dispatchingUp_p[t]) for t in b.TIME_s]
        fig.add_trace(go.Scatter(
            x = time,
            y = FLEX_UP_DIS_96,
            name = f'Dispatched Upward Flexibility [kW]',
            opacity = .5,
            hovertext= ['Value: {:.2f}'.format(val) for val in FLEX_UP_DIS_96]),
            row=3,
            col=1) 
        
        my_base = [0 for t in b.TIME_s]

        fig.add_trace(go.Bar(
            x = time,
            y = FLEX_UP_ACT_96,
            base = my_base,
            name = f'Provided Upward Flexibility [kW]',
            opacity = .5,
            hovertext= ['Value: {:.2f}'.format(val) for val in FLEX_UP_ACT_96],
            offsetgroup = 0),
            row=3,
            col=1)
        my_base = [my_base[t-1] + FLEX_UP_ACT_96[t-1] for t in b.TIME_s]

        FLEX_UP_SLACK_96 = [_v(b.model().FLEX_b["FLEX_1"].power_localFlex_slackUp_v[t]) for t in b.TIME_s]  
        fig.add_trace(go.Bar(
            x = time,
            y = FLEX_UP_SLACK_96,
            base = my_base,
            name = f'Un-provided Upward Flexibility (Slack) [kW]',
            opacity = .5,
            hovertext= ['Value: {:.2f}'.format(val) for val in FLEX_UP_SLACK_96],
            offsetgroup = 0),
            row=3,
            col=1)
                
    # Update layout
    fig.update_layout(
        title=f"Flex Up Balance - {name}",
        title_x=0.5,
        barmode = "stack",
        xaxis_title="Time Step",
        xaxis1 = dict(range=xrange, tickvals=xticks, ticktext=xtext),
        yaxis=dict(title="kW"), #range=[0, 4000]),  # Primary y-axis for power fluxes
        yaxis2=dict(title="kW"),
        yaxis3=dict(title="kW"),
        legend=dict(title="Legend"),
        template="plotly_white",
        height=800  # Adjust the height for better visualization
    )

    address = f'{folder}/Reports/{name}.html'
    uri = pathlib.Path(address).absolute().as_uri()
    
    with open(address, 'w') as f:
        f.write(fig.to_html(full_html=True, include_plotlyjs='cdn'))
       
    uri = pathlib.Path(address).absolute().as_uri()
    webbrowser.open(uri)    


def el_save_results(b, name, folder):  
    #Create dataframe with time-indexed variables
    
    time_indexed = pd.DataFrame()
    time_indexed['Index'] = [t for t in b.TIME_s]
    time_indexed.set_index("Index", inplace=True)
    
    time_indexed['power_totalProduction_v'] = [b.power_totalProduction_v[t].value for t in b.TIME_s]

    
    # Create series with static variables
    static = pd.DataFrame()
    
    return (time_indexed, static)

def ng_save_results(b, name, folder):
    
    #Create dataframe with time-indexed variables
    
    time_indexed = pd.DataFrame()
    time_indexed['Index'] = [t for t in b.TIME_s]
    time_indexed.set_index("Index", inplace=True)
    
    time_indexed['energy_NGforElectricity_v'] = [b.energy_NGforElectricity_v[t].value for t in b.TIME_s]
    time_indexed['energy_NGtotalConsumption_v'] = [b.energy_NGtotalConsumption_v[t].value for t in b.TIME_s]

    
    # Create series with static variables
    static = pd.DataFrame()
    
    return (time_indexed, static)

def th_save_results(b, name, folder):
    
    #Create dataframe with time-indexed variables
    
    time_indexed = pd.DataFrame()
    time_indexed['Index'] = [t for t in b.TIME_s]
    time_indexed.set_index("Index", inplace=True)
    
    time_indexed['power_heatTotalProduction_v'] = [b.power_heatTotalProduction_v[t].value for t in b.TIME_s]
    
    # Create series with static variables
    static = pd.DataFrame()
    
    return (time_indexed, static)

def flex_save_results(b, name, folder):
    
    #Create dataframe with time-indexed variables
    
    time_indexed = pd.DataFrame()
    time_indexed['Index'] = [t for t in b.TIME_s]
    time_indexed.set_index("Index", inplace=True)
    
    time_indexed['baseline_p'] = [b.baseline_p[t] for t in b.TIME_s]
    
    # Create series with static variables
    static = pd.DataFrame()
    
    return (time_indexed, static)


def create_reportFlow(b,name,folder): 
    import pandas as pd 
    
    b.TIME_s = Set(initialize=b.model().TIME_s)
    
    time = [t for t in b.TIME_s]
    
    nodes = [n for n in b.NODE_s]
    nodes_num = range(0, len(nodes))
    
    
    links_num = [(i,j) for i in nodes_num for j in nodes_num]
    links = [(i,j) for i in nodes for j in nodes]
    
    
    
    sources = [i for (i,j) in links_num]
    targets = [j for (i,j) in links_num]
    
    connections = [b.logic_isConnectedGraph_p[i,j] for (i,j) in links]
    values = [sum(b.power_flow_v[i,j,t].value for t in time) for (i,j) in links]
    
    fig = make_subplots(
        rows=1, cols=1,
        subplot_titles=("Connections"),
        )
    
    trace1 = (go.Sankey(
        node = dict(
            pad = 15,
            thickness = 15,
            line = dict(color="black", width = 0.5),
            label = nodes          
            ),
        link = dict(
            arrowlen = 15,
            source = sources,
            target = targets,
            value = connections
            ),
            domain = {
                'x': [0, 0.45]}
        ))  
    
    trace2 = (go.Sankey(
        node = dict(
            pad = 15,
            thickness = 15,
            line = dict(color="black", width = 0.5),
            label = nodes          
            ),
        link = dict(
            arrowlen = 15,
            source = sources,
            target = targets,
            value = values
            ),domain = {
                'x': [0.55, 1]}

        )) 
    
    data = [trace1, trace2]
    
    layout = go.Layout(
        title = f'Sankey Diagram - {name}',
        title_x=0.5,
        template="plotly_white"
        )
    
    fig = go.Figure(data=data, layout=layout)
    
    fig.update_layout(height=500, title_text=f'Sankey Diagram - {name}',title_x=0.5, showlegend=True,
                      template="plotly_white",
                      )        
    
    
    
    address = f'{folder}/Reports/{name}.html'
    uri = pathlib.Path(address).absolute().as_uri()
    
    with open(address, 'w') as f:
        f.write(fig.to_html(full_html=True, include_plotlyjs='cdn'))
       
    uri = pathlib.Path(address).absolute().as_uri()
    webbrowser.open(uri) 


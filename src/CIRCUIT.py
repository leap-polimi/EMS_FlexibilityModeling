# -*- coding: utf-8 -*-
"""
Energy Management System (EMS) - CIRCUITs reporting routines
Copyright (C) 2020-2024 LEAP scarl
Authors:
- Matteo Zatti
- Marco Gabba
- Filippo Bovera

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
        rows=1, cols=1,
        subplot_titles=("Electricity Balance"),
        shared_yaxes=True
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
            hovertext= ['Value: {:.2f}'.format(val) for val in EL_OUT])) 
    
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
            offsetgroup = 0))
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
            offsetgroup = 0))
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
            offsetgroup = 0))
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
            offsetgroup = 1))
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
            offsetgroup = 1))
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
            offsetgroup = 1))
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
            offsetgroup = 1))
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
           offsetgroup = 1))
       my_base = [my_base[t-1] + EL_IN[t-1] for t in b.TIME_s]
       

    if b.model().logic_schedulingReschedulingSelection_p==1:       
        for p in b.CONNECTED_POD_s:
            EL_IN=[pyo.value(b.model().POD_b[p].BDE_Down_v[t]) for t in b.TIME_s]
            fig.add_trace(go.Scatter(
                x = time,
                y = EL_IN,
                line= dict(color='red', width=3, dash='solid'),
                name = f'BDE Down - {p} [kW]',
                opacity = .5,
                hovertext= ['Value: {:.2f}'.format(val) for val in EL_IN]
                ))
        
        for p in b.CONNECTED_POD_s:
            EL_OUT=[pyo.value(b.model().POD_b[p].baselineWithdrawn_p[t]-b.model().POD_b[p].baselineInjected_p[t]) for t in b.TIME_s]
            fig.add_trace(go.Scatter(
                x = time,
                y = EL_OUT,
                line= dict(color='black', width=3, dash='solid'),
                name = f'Baseline- {p} [kW]',
                opacity = .5,
                hovertext= ['Value: {:.2f}'.format(val) for val in EL_OUT]
                ))       
        for p in b.CONNECTED_POD_s:
            EL_OUT=[pyo.value(b.model().POD_b[p].BDE_Up_v[t]) for t in b.TIME_s]
            fig.add_trace(go.Scatter(
                x = time,
                y = [-val for val in EL_OUT],
                line= dict(color='green', width=3, dash='solid'),
                name = f'BDE Up- {p} [kW]',
                opacity = .5,
                hovertext= ['Value: {:.2f}'.format(val) for val in EL_OUT]
                ))
        
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
        subplot_titles=("Thermal Balance"),
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
    


#Input of Thermal Balance - Each GENSET + COGEN + BESS ( DISCHARGED )+  PV + POD (WITHDRAWN)
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
        subplot_titles=("Electricity Balance"),
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

#Input of Natural GAS Balance - Each GENSET + COGEN 

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
            name = f'BOILER Production - {u} [kW fuel]',
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


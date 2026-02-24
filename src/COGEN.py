# -*- coding: utf-8 -*-
"""
Energy Management System (EMS) - CHP block
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

from pyomo.core import AbstractModel,Set,RangeSet,Param,Var,Constraint, Objective, minimize, NonNegativeIntegers,NonNegativeReals,Binary, Block, Reals
import pyomo.environ as pyo

def create_block(b,g):
    #SETS
    b.TIME_s = Set(initialize=b.model().TIME_s) # CRITICAL -> we're referencing the parent model within the child model, BUT at least is decoupled
    b.TIME_before_s = Set(initialize=b.model().TIME_before_s)
    b.timestep_size_p = Param(initialize=b.model().timestep_size_p) # [hours] Duration of the timestep 

    b.eff_pieces_p = Param(within=NonNegativeIntegers, default=5) #:param eff_pieces_p: number of pieces used for describing the CHP el. and th. efficiency curves
    b.eff_pieces_s = RangeSet(b.eff_pieces_p) # [1,2,3,...]
    
    @b.Param()
    def timesteps_before_p(b):
        return len(b.TIME_before_s)
    
    # .. section::TIME-INDEPENDENT PARAMETERS
    b.power_electricityNominal_p = Param(within=NonNegativeReals) #:param power_electricityNominal_p: Nominal power of the COGEN (output) [kWel]
    b.power_electricityMin_p = Param(within=NonNegativeReals) #:param power_electricityMin_p: Minimum Load (electricity) for the COGEN, expressed as p.u. of power_electricityNominal_p [pu]
    b.power_electricityMax_p = Param(within=NonNegativeReals) #:param :Maximum Load (electricity)for the COGEN, expressed as p.u. of power_heatNominal_p [pu]
    
    #Piecewise linearization of the electrical efficiency (5 'pieces')
    b.efficiency_electricitySlope_p = Param(b.eff_pieces_s, within=Reals) #:param efficiency_electricitySlope_p: Slope term for part-load output calculation
    b.efficiency_electricityIntercept_p = Param(b.eff_pieces_s, within=Reals) #:param efficiency_electricityIntercept_p: Intercept term for part-load output calculation

    #Piecewise linearization of the heat efficiency (5 'pieces')
    b.efficiency_heatSlope_p = Param(b.eff_pieces_s, within=Reals) #:param efficiency_heatSlope_p: Slope term for part-load output calculation
    b.efficiency_heatIntercept_p = Param(b.eff_pieces_s, within=Reals) #:param efficiency_heatIntercept_p: Intercept term for part-load output calculation

    b.fuelInputLowerBound_p = Param(b.eff_pieces_s, within=NonNegativeReals) #:param fuelInputLowerBound_p: [kW] Lower value of the fuelInput-interval selected for the efficiency curves approx
    b.fuelInputUpperBound_p = Param(b.eff_pieces_s, within=NonNegativeReals) #:param fuelInputUpperBound_p: [kW] Upper value of the fuelInput-interval selected for the efficiency curves approx

    b.logic_isPiecewiseEfficiency_p = Param(within= Binary, default=0) #:param logic_isPiecewiseEfficiency_p: [-] Binary parameter indicating if we are using the piecewise efficiency curve

    # Single linearization of the efficiency curves (1 piece)
    b.efficiency_electricitySlope_simple_p = Param(within=Reals) #:param efficiency_electricitySlope_p: Slope term for part-load output calculation
    b.efficiency_electricityIntercept_simple_p = Param(within=Reals) #:param efficiency_electricityIntercept_p: Intercept term for part-load output calculation
    b.efficiency_heatSlope_simple_p = Param(within=Reals) #:param efficiency_electricitySlope_p: Slope term for part-load output calculation
    b.efficiency_heatIntercept_simple_p = Param(within=Reals) #:param efficiency_electricityIntercept_p: Intercept term for part-load output calculation

    b.power_electricityRampUp_p = Param(within=NonNegativeReals) #:param power_electricityRampUp_p: Max ramp-up in the timestep in terms of per-unit of output power (electricity) [pu]
    b.power_electricityRampDown_p = Param(within=NonNegativeReals) #:param power_electricityRampDown_p:Max ramp-down in the timestep in terms of per-unit of output power (electricity) [pu]
    b.power_electricityStartUp_p = Param(within=NonNegativeReals) #:param power_electricityStartUp_p: [pu] Max power output after the end of start-up procedure  NB: In slow-machine this parameter should be equal to 0
    b.power_electricityShutDown_p = Param(within=NonNegativeReals) #:param power_electricityShutDown_p: [pu] Max power output after the beginning of shut-down procedure NB: In slow-machine this parameter should be equal to 0
    b.timesteps_minimumTimeOn_p = Param(within=NonNegativeIntegers) #:param timesteps_minimumTimeOn_p:  Number of timesteps the machine must stay active after startup timestep [timesteps]
    b.timesteps_minimumTimeOff_p = Param(within=NonNegativeIntegers) #:param timesteps_minimumTimeOff_p: Number of timesteps the machine must stay off after shutdown timestep [timesteps]
    b.cost_operationMaintenanceTimestep_p = Param(within=NonNegativeReals) #:param cost_operationMaintenanceTimestep_p: cost for operation and maintenance of the machine expressed as € per timestep of operation [€ / timestep]
    b.energy_NGforElectricity_p = Param(within=NonNegativeReals, default=2.112) #:param energy_NGforElectricity: [Sm3/kWh_el] fraction of NG used for electricity production (0.220 Sm3 for kWh_el)
    
    @b.Param (within=NonNegativeReals)
    def power_heatNominal_p (b): #:param power_heatNominal_p: Nominal thermal power of the COGEN (output) [kW]
        fuel_input = (b.power_electricityNominal_p - b.efficiency_electricityIntercept_p)/b.efficiency_electricitySlope_p
        return b.efficiency_heatSlope_p*fuel_input+b.efficiency_heatIntercept_p
    
    @b.Param (within=NonNegativeReals)
    def power_heatMax_p (b): #:param power_heatMax_p: Maximum Load (thermal) for the COGEN [pu]
        fuel_input = (b.power_electricityNominal_p *  b.power_electricityMax_p - b.efficiency_electricityIntercept_p)/b.efficiency_electricitySlope_p
        return (b.efficiency_heatSlope_p*fuel_input+b.efficiency_heatIntercept_p)/b.power_heatNominal_p
    
    @b.Param (within=NonNegativeReals)
    def power_heatMin_p (b): #:param power_heatMin_p: Minimum Load (thermal) for the COGEN [pu]
        fuel_input = (b.power_electricityNominal_p *b.power_electricityMin_p - b.efficiency_electricityIntercept_p)/b.efficiency_electricitySlope_p
        return (b.efficiency_heatSlope_p*fuel_input+b.efficiency_heatIntercept_p)/b.power_heatNominal_p
        
    b.cost_startUp_p=Param(within=NonNegativeReals) #:param cost_startUp_p: [€] cost of start-up event
    b.cost_shutDown_p=Param(within=NonNegativeReals) #:param cost_shutDown_p: [€] cost of shut-down event
    b.timesteps_startUpDuration_p=Param(within=NonNegativeIntegers) #:param timesteps_startUpDuration_p: [timesteps] duration of the start-up procedure. NB: for fast-machine this parameter should be equal to 0 
    b.timesteps_shutDownDuration_p=Param(within=NonNegativeIntegers) #:param timesteps_shutDownDuration_p: [timesteps] duration of the shut-down procedure NB: for fast-machine this parameter should be equal to 0
    
    # .. section:: INITIALIZATION PARAMETERS
    b.logic_isOn_before_p = Param(b.TIME_before_s, within=Binary)  #:param logic_isOn_before_p:  [-] 1 = The machine is on during this timestep, otherwise 0; values outside optimization window;
    b.logic_isStartingUp_before_p = Param(b.TIME_before_s, within=Binary) #:param logic_isStartingUp_before_p: [-] 1 = Machine is beginning start-up procedure during this timestep, otherwise 0
    b.logic_isShuttingDown_before_p = Param(b.TIME_before_s, within=Binary) #:param logic_isShuttingDown_before_p: [-] 1 = Machine is at the start of shut-down procedure during this timestep, otherwise 0
    b.power_electricityOutput_before_p = Param(b.TIME_before_s, within=NonNegativeReals) #:param power_electricityOutput_before_p: Output of the COGEN (electricity) outside optimization window [kW_el] 
    
    # .. section:: TIME-DEPENDENT PARAMETERS
    b.logic_is_trackmode_on_p = Param(b.TIME_s, within=Binary, default=0) #:param logic_is_trackmode_on_p: [-] Binary to see if trackmode is on
    b.track_mode_p = Param(b.TIME_s, within=NonNegativeIntegers) #:param track_mode_p: [-] Definition of the TRACK MODE: 1 EL - 2 TH - 3 MAX
    b.logic_is_available_p = Param(b.TIME_s, within=Binary, default=1) #:param logic_is_available_p: [-] 1 = the machine is available in this timestep
    b.logic_must_run_p = Param (b.TIME_s, within=Binary, default=0) #:param logic_must_run_p: [-] 1 = the machine must be switched on
    b.logic_is_controllable_electricity_p = Param (b.TIME_s, within=Binary, default=1) #:param logic_is_controllable_electricity_p: [-] 1= the machine can be controlled by the EMS and an electrical power should be set
    b.logic_is_controllable_heat_p = Param (b.TIME_s, within=Binary, default=1) #:param logic_is_controllable_heat_p: [-] 1= the machine can be controlled by the EMS and a thermal power should be set
    b.power_setpointheatOutput_p = Param (b.TIME_s, within=NonNegativeReals, default=0.0) #:param power_setpointheatOutput_p: [kW] if not controllable, this parameters set the thermal power of the machine
    b.power_setpointElectricityOutput_p = Param (b.TIME_s, within=NonNegativeReals, default=0.0) #:param power_setpointElectricityOutput_p: [kW] if not controllable, this parameters set the electrical power of the machine
    
    b.logic_isCRAllowed_p = Param (b.TIME_s, within = Binary, default=1) #:param logic_isCRAllowed_p: [1] device is allowed to participate into CR programs 
    
    #.. section:: VARS
    b.power_fuelInput_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_fuelInput_v: [kW_fuel] Input of the COGEN, in terms of mean power input in the timestep
    b.power_heatOutput_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_heatOutput_v: [kW_th] Output of the COGEN (heat), in terms of mean power output in the timestep
    b.power_electricityOutput_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_electricityOutput_v: [kW_el] Output of the COGEN (electricity), in terms of mean power output in the timestep

    b.logic_efficiencySelection_v = Var(b.TIME_s, b.eff_pieces_s, within=Binary) #:var logic_efficiencySelection: =1 to select a specific piece of the efficiency curves
    
    b.power_electricityActual_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_electricityActual_v: [kW_el] HELPER VAR - Actual output that can be supplied by the COGEN (e.g. 0 if is not on)
    b.power_heatActual_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_heatActual_v: [kW_th] HELPER VAR - Actual output that can be supplied by the COGEN (e.g. 0 if is not on)
    
    b.logic_isOn_v = Var(b.TIME_s, within=Binary) #:param logic_isOn_v: [-] 1 = The machine is on during this timestep, otherwise 0
    b.logic_isStartingUp_v = Var(b.TIME_s, within=Binary) #:param logic_isStartingUp_v: [-] 1 = Machine is beginning start-up procedure during this timestep, otherwise 0
    b.logic_isShuttingDown_v = Var(b.TIME_s, within=Binary) #:param logic_isShuttingDown_v:  [-] 1 = Machine is at the start of shut-down procedure during this timestep, otherwise 0
    
    b.cost_operationMaintenance_v = Var(within=NonNegativeReals) #:param cost_operationMaintenance_v: [€] Total cost for O&M incurred by the COGEN
    
    b.power_capacityRetentionUp_v = Var(b.TIME_s,within=Reals) #:param power_capacityRetentionUp_v: [kW_el] Capacity Retention upwards available for the GENSET
    b.power_capacityRetentionDown_v = Var(b.TIME_s,within=Reals) #:param power_capacityRetentionDown_v: [kW_el] Capacity Retention downwards available for the GENSET
    
    b.energy_NGforElectricity_v = Var(b.TIME_s,within=NonNegativeReals) #:param energy_NGforElectricity_v: [Sm3] NG used for electricity production
    
    #CONSTRAINTS
    @b.Constraint(b.TIME_s)
    def Cogen_availability(b,t):
        if b.logic_is_available_p [t] == 0 :
           return b.logic_isOn_v[t] == 0
        else:
            return Constraint.Skip
    
    @b.Constraint(b.TIME_s)
    def Cogen_electricityActual_power(b,t):
        return b.power_electricityActual_v[t] == b.logic_isOn_v[t]*b.power_electricityNominal_p
       
    @b.Constraint(b.TIME_s)
    def Cogen_heatActual_power(b,t):
        return b.power_heatActual_v[t] == b.logic_isOn_v[t]*b.power_heatNominal_p
    
    @b.Constraint(b.TIME_s)
    def Cogen_electricityProduction(b,t):
        if b.logic_isPiecewiseEfficiency_p == 0:
            return b.power_electricityOutput_v[t] == b.efficiency_electricitySlope_simple_p*b.power_fuelInput_v[t]+b.efficiency_electricityIntercept_simple_p*b.logic_isOn_v[t]
        else:
            return b.power_electricityOutput_v[t] == sum((b.efficiency_electricitySlope_p[p]*b.power_fuelInput_v[t]+b.efficiency_electricityIntercept_p[p]*b.logic_isOn_v[t])*b.logic_efficiencySelection_v[t,p] for p in b.eff_pieces_s)
    
    @b.Constraint(b.TIME_s)
    def Cogen_heatProduction(b,t):
        if b.logic_isPiecewiseEfficiency_p == 0:
            return b.power_heatOutput_v[t] == b.efficiency_heatSlope_simple_p*b.power_fuelInput_v[t]+b.efficiency_heatIntercept_simple_p*b.logic_isOn_v[t]
        else:
            return b.power_heatOutput_v[t] == sum((b.efficiency_heatSlope_p[p]*b.power_fuelInput_v[t]+b.efficiency_heatIntercept_p[p]*b.logic_isOn_v[t])*b.logic_efficiencySelection_v[t,p] for p in b.eff_pieces_s)
        
    @b.Constraint(b.TIME_s)
    def Cogen_efficiency_Selection(b,t):
        if b.logic_isPiecewiseEfficiency_p == 0:
            return Constraint.Skip
        else:
            return sum(b.logic_efficiencySelection_v[t,p] for p in b.eff_pieces_s) == 1
    
    @b.Constraint(b.TIME_s, b.eff_pieces_s)
    def Cogen_EfficiencySelection_Lower(b, t, p):
        if b.logic_isPiecewiseEfficiency_p == 0:
            return Constraint.Skip
        else:
            return b.power_fuelInput_v[t] >= b.fuelInputLowerBound_p[p] - b.bigM_p * (1 - b.logic_efficiencySelection_v[t, p])

    @b.Constraint(b.TIME_s, b.eff_pieces_s)
    def Cogen_EfficiencySelection_Upper(b, t, p):
        if b.logic_isPiecewiseEfficiency_p == 0:
            return Constraint.Skip
        else:
            return b.power_fuelInput_v[t] <= b.fuelInputUpperBound_p[p] + b.bigM_p * (1 - b.logic_efficiencySelection_v[t, p])

    # OUTPUT is constrained by technical max load and min load
    @b.Constraint(b.TIME_s)
    def Cogen_electricityProduction_LB(b,t):
        return b.power_electricityOutput_v[t] >= b.power_electricityMin_p*b.power_electricityActual_v[t]
    
    @b.Constraint(b.TIME_s)
    def Cogen_electricityProduction_UB(b,t):
        return b.power_electricityOutput_v[t] <= b.power_electricityMax_p*b.power_electricityActual_v[t]
    
     
    # OUTPUT is constrained by ramp limit, taking also in account start-ups and shut-downs 
    @b.Constraint(b.TIME_s)
    def Cogen_electricityRampup_startup_limit(b,t):
        if b.logic_is_available_p[t] == 1 :
            if t == b.TIME_s.first():
                prev_t = b.TIME_before_s.last()
                if b.timesteps_startUpDuration_p !=0: #slow machine
                    t_startUp=b.TIME_before_s[-b.timesteps_startUpDuration_p]
                    return b.power_electricityOutput_v[t]-b.power_electricityOutput_before_p[prev_t] <= b.power_electricityRampUp_p*b.power_electricityNominal_p*b.logic_isOn_before_p[prev_t] + b.logic_isStartingUp_before_p[t_startUp]*(b.power_electricityStartUp_p+b.power_electricityMin_p)*b.power_electricityNominal_p     
                else: #fast machine
                    t_startUp = t
                    return b.power_electricityOutput_v[t]-b.power_electricityOutput_before_p[prev_t] <= b.power_electricityRampUp_p*b.power_electricityNominal_p*b.logic_isOn_before_p[prev_t] + b.logic_isStartingUp_v[t_startUp]*(b.power_electricityStartUp_p+b.power_electricityMin_p)*b.power_electricityNominal_p     
            else:
                prev_t = b.TIME_s.prev(t)
                if t <= b.timesteps_startUpDuration_p and b.timesteps_startUpDuration_p != 0: #slow machine
                    t_startUp = t-b.timesteps_startUpDuration_p
                    return b.power_electricityOutput_v[t]-b.power_electricityOutput_v[prev_t] <= b.power_electricityRampUp_p*b.power_electricityActual_v[prev_t] + b.logic_isStartingUp_before_p[t_startUp]*(b.power_electricityStartUp_p+b.power_electricityMin_p)*b.power_electricityNominal_p
                else: # slow machine with t>timesteps_startUpDuration & fast-machine
                    t_startUp = t-b.timesteps_startUpDuration_p
                    return b.power_electricityOutput_v[t]-b.power_electricityOutput_v[prev_t] <= b.power_electricityRampUp_p*b.power_electricityActual_v[prev_t] + b.logic_isStartingUp_v[t_startUp]*(b.power_electricityStartUp_p+b.power_electricityMin_p)*b.power_electricityNominal_p
        else:
            return Constraint.Skip
        
    @b.Constraint(b.TIME_s)
    def Cogen_electricityRampdown_shutdown_limit(b,t):
        if b.logic_is_available_p[t] == 1 :
            if t == b.TIME_s.first():
                prev_t = b.TIME_before_s.last()
                return b.power_electricityOutput_before_p[prev_t]-b.power_electricityOutput_v[t] <= b.power_electricityRampDown_p*b.power_electricityActual_v[t] + b.logic_isShuttingDown_v[t]*(b.power_electricityShutDown_p+b.power_electricityMin_p)*b.power_electricityNominal_p
            else:
                prev_t = b.TIME_s.prev(t)
                return b.power_electricityOutput_v[prev_t]-b.power_electricityOutput_v[t] <= b.power_electricityRampDown_p*b.power_electricityActual_v[t] + b.logic_isShuttingDown_v[t]*(b.power_electricityShutDown_p+b.power_electricityMin_p)*b.power_electricityNominal_p
        else:
            return Constraint.Skip
       
    # Start-up and shut-down determine if the machine is on/off
    @b.Constraint(b.TIME_s)
    def Cogen_startup_shutdown(b,t):
        if t == b.TIME_s.first():
            prev_t = b.TIME_before_s.last()
            if b.timesteps_startUpDuration_p !=0: #slow machine
                t_startUp = b.TIME_before_s[-b.timesteps_startUpDuration_p]
                return b.logic_isStartingUp_before_p[t_startUp] - b.logic_isShuttingDown_v[t] == b.logic_isOn_v[t] - b.logic_isOn_before_p[prev_t]
            else: #fast machine
                t_startUp = t
                return b.logic_isStartingUp_v[t_startUp] - b.logic_isShuttingDown_v[t] == b.logic_isOn_v[t] - b.logic_isOn_before_p[prev_t]
        else:
            prev_t = b.TIME_s.prev(t)
            if t <= b.timesteps_startUpDuration_p and b.timesteps_startUpDuration_p != 0: #slow machine 
                t_startUp = t-b.timesteps_startUpDuration_p
                return b.logic_isStartingUp_before_p[t_startUp] - b.logic_isShuttingDown_v[t] == b.logic_isOn_v[t] - b.logic_isOn_v[prev_t]
            else: # slow machine with t>timesteps_startUpDuration & fast-machine
                t_startUp = t-b.timesteps_startUpDuration_p
            return b.logic_isStartingUp_v[t_startUp] - b.logic_isShuttingDown_v[t] == b.logic_isOn_v[t] - b.logic_isOn_v[prev_t]
    
    
    # If I'm starting up I cannot be shutting down
    @b.Constraint(b.TIME_s)
    def Cogen_startup_shutdown_dicotomy(b,t):
        if t == b.TIME_s.first():
            if b.timesteps_startUpDuration_p !=0:
                t_startUp = b.TIME_before_s[-b.timesteps_startUpDuration_p]
                return b.logic_isStartingUp_before_p[t_startUp] - b.logic_isShuttingDown_v[t] <= 1
            else:
                t_startUp = t
        else:
            if t <= b.timesteps_startUpDuration_p and b.timesteps_startUpDuration_p != 0: #slow machine 
                t_startUp = t-b.timesteps_startUpDuration_p
                return b.logic_isStartingUp_before_p[t_startUp] - b.logic_isShuttingDown_v[t] <= 1
            else: # slow machine with t>timesteps_startUpDuration & fast-machine
                t_startUp = t-b.timesteps_startUpDuration_p
        return b.logic_isStartingUp_v[t_startUp] + b.logic_isShuttingDown_v[t] <= 1
    
    # Minimum up-time and minimum downtime
    @b.Constraint(b.TIME_s)
    def Cogen_minimum_uptime(b,t):
        if b.logic_is_available_p[t] == 1 :
            if t <= b.timesteps_minimumTimeOn_p:
                value = \
                    sum(b.logic_isOn_v[tau] for tau in range(1,t)) \
                        + sum(b.logic_isOn_before_p[tau_neg] for tau_neg in range(-b.timesteps_minimumTimeOn_p+t,1))    
            else:
                value = sum(b.logic_isOn_v[tau] for tau in range(t-b.timesteps_minimumTimeOn_p,t))
            
            return b.logic_isShuttingDown_v[t] <= value/b.timesteps_minimumTimeOn_p
        else:
            return Constraint.Skip
    
    @b.Constraint(b.TIME_s)
    def Cogen_minimum_downtime(b,t):
        if b.logic_is_available_p[t] == 1 :
            timesteps_from_shutDown = b.timesteps_minimumTimeOff_p+b.timesteps_shutDownDuration_p-1
            if t <= timesteps_from_shutDown:
                value = \
                    sum(b.logic_isOn_v[tau] for tau in range(1,t)) \
                  + sum(b.logic_isOn_before_p[tau_neg] for tau_neg in range(-timesteps_from_shutDown+t,1))    
            else:
                value = sum(b.logic_isOn_v[tau] for tau in range(t-timesteps_from_shutDown,t))
            return b.logic_isStartingUp_v[t] <= 1-value/(timesteps_from_shutDown+1)
        else:
            return Constraint.Skip
        
    @b.Constraint()
    def Cogen_operationMaintenance_cost_calc(b):
        return b.cost_operationMaintenance_v == sum(b.cost_operationMaintenanceTimestep_p*b.logic_isOn_v[t] for t in b.TIME_s)
    
    @b.Constraint(b.TIME_s)
    def capacity_retention_up_calc(b,t):
        if b.logic_is_available_p[t] == 1 :
            prod_max = b.power_electricityNominal_p.value*b.power_electricityMax_p.value*b.logic_isOn_v[t]
            return b.power_capacityRetentionUp_v[t] <= prod_max - b.power_electricityOutput_v[t]
        else:
            return Constraint.Skip
    
    @b.Constraint(b.TIME_s)
    def capacity_retention_down_calc(b,t):
        if b.logic_is_available_p[t] == 1 :
            prod_min = b.power_electricityNominal_p.value*b.power_electricityMin_p.value*b.logic_isOn_v[t]
            return b.power_capacityRetentionDown_v[t] <= b.power_electricityOutput_v[t] - prod_min
        else:
            return Constraint.Skip

    @b.Constraint(b.TIME_s)
    def CR_allowed_UP(b,t):
        if b.logic_isCRAllowed_p[t] == 0:
            return b.power_capacityRetentionUp_v[t] == 0
        else:
            return Constraint.Skip
        
    @b.Constraint(b.TIME_s)
    def CR_allowed_DOWN(b,t):
        if b.logic_isCRAllowed_p[t] == 0:
            return b.power_capacityRetentionDown_v[t] == 0
        else:
            return Constraint.Skip


    #Must run logics 
    @b.Constraint(b.TIME_s)
    def Cogen_must_run(b,t):
        if b.logic_is_available_p[t] == 1 :
            return b.logic_isOn_v[t]>=b.logic_must_run_p[t]
        else:
            return Constraint.Skip
    
       # CONTROLLABILITY: IF NOT CONTROLLABLE, I NEED TO PROVIDE A SET POINT # 
    @b.Constraint(b.TIME_s)
    def Cogen_controllability_EL(b,t):
        if b.logic_is_controllable_electricity_p[t] == 1:
            return Constraint.Skip
        else:
            return b.power_electricityOutput_v[t] == b.power_setpointElectricityOutput_p[t]*b.logic_is_available_p[t]
    
    @b.Constraint(b.TIME_s)
    def Cogen_controllability_TH(b,t):
        if b.logic_is_controllable_heat_p[t] == 1:
            return Constraint.Skip
        else:
            return b.power_heatOutput_v[t] == b.power_setpointheatOutput_p[t]*b.logic_is_available_p[t]
            
    @b.Constraint(b.TIME_s)
    def NGforElectricity_CALC(b,t):
        return b.energy_NGforElectricity_v[t] == b.power_electricityOutput_v[t]*b.timestep_size_p*b.energy_NGforElectricity_p
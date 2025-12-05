# -*- coding: utf-8 -*-
"""
Energy Management System (EMS) - ELECTRIC GENERATOR (GENSET) block
Copyright (C) 2020-2024 LEAP - Authors: M.Zatti, M. Gabba, F. Bovera

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

from pyomo.core import Set,RangeSet,Param,Var,Constraint,NonNegativeReals,NonNegativeIntegers, Binary,Reals

def create_block(b,g):

    #SETS  
    b.TIME_s = Set(initialize=b.model().TIME_s) # CRITICAL -> we're referencing the parent model within the child model, BUT at least is decoupled
    b.TIME_before_s = Set(initialize=b.model().TIME_before_s)
    b.timestep_size_p = Param(initialize=b.model().timestep_size_p) # [hours] Duration of the timestep 
    
    @b.Param()
    def timesteps_before_p(b):
        return len(b.TIME_before_s)
    
  
    # .. section::TIME-INDEPENDENT PARAMETERS
    b.power_nominal_p = Param(within=NonNegativeReals) #:param power_nominal_p: Nominal power of the GENSET (output)[kWel]
    b.power_min_p = Param(within=NonNegativeReals) #:param power_min_p: Minimum Load for the machine, expressed as p.u. of power_nominal_p [pu] 
    b.power_max_p = Param(within=NonNegativeReals) #:param power_max_p: Maximum Load for the machine, expressed as p.u. of power_nominal_p [pu] 
    b.efficiency_slope_p = Param(within=Reals) #:param efficiency_slope_p: Slope term for part-load output calculation
    b.efficiency_intercept_p = Param(within=Reals) #:param efficiency_intercept_p: Intercept term for part-load output calculation
    b.power_rampUp_p = Param(within=NonNegativeReals) #:param power_rampUp_p: Max ramp-up in the timestep in terms of per-unit of output power  [pu]
    b.power_rampDown_p = Param(within=NonNegativeReals) #:param power_rampDown_p: Max ramp-down in the timestep in terms of per-unit of output power [pu] 
    b.power_startUp_p = Param(within=NonNegativeReals) #:param power_startUp_p: [pu] Max power output after the end of start-up procedure  NB: In slow-machine this parameter should be equal to 0
    b.power_shutDown_p = Param(within=NonNegativeReals) #:param power_shutDown_p: [pu] Max power output after the beginning of shut-down procedure NB: In slow-machine this parameter should be equal to 0
    
    b.timesteps_minimumTimeOn_p = Param(within=NonNegativeIntegers) #:param timesteps_minimumTimeOn_p: Number of timesteps the machine must stay active after startup timestep [timesteps] 
    b.timesteps_minimumTimeOff_p = Param(within=NonNegativeIntegers) #:param timesteps_minimumTimeOff_p: Number of timesteps the machine must stay off after shutdown timestep [timesteps] 
    b.cost_operationMaintenanceTimestep_p = Param(within=NonNegativeReals) #:param cost_operationMaintenanceTimestep_p: cost for operation and maintenance of the machine expressed as € per timestep of operation [€ / timestep] 
    
    b.cost_startUp_p=Param(within=NonNegativeReals) #:param cost_startUp_p: [€] cost of start-up event
    b.cost_shutDown_p=Param(within=NonNegativeReals) #:param cost_shutDown_p: [€] cost of shut-down event
    b.timesteps_startUpDuration_p=Param(within=NonNegativeIntegers) #:param timesteps_startUpDuration_p: [timesteps] duration of the start-up procedure. NB: for fast-machine this parameter should be equal to 0 
    b.timesteps_shutDownDuration_p=Param(within=NonNegativeIntegers) #:param timesteps_shutDownDuration_p: [timesteps] duration of the shut-down procedure NB: for fast-machine this parameter should be equal to 0
    
    # .. section::INITIALIZATION PARAMETERS
    b.logic_isOn_before_p = Param(b.TIME_before_s, within=Binary)  #:param logic_isOn_before_p: [-] 1 = The machine is on during this timestep, otherwise 0; values outside optimization window;
    b.logic_isStartingUp_before_p = Param(b.TIME_before_s, within=Binary) #:param logic_isStartingUp_before_p: [-] 1 = Machine is beginning start-up procedure during this timestep, otherwise 0
    b.logic_isShuttingDown_before_p = Param(b.TIME_before_s, within=Binary) #:param logic_isShuttingDown_before_p: [-] 1 = Machine is at the start of shut-down procedure during this timestep, otherwise 0
    
    b.power_electricityOutput_before_p = Param(b.TIME_before_s, within=NonNegativeReals) #:param power_electricityOutput_before_p: Output of the GENSET outside optimization window [kW_el]
    
    # .. section::TIME-DEPENDENT PARAMETERS
    b.logic_is_available_p = Param(b.TIME_s, within=Binary, default=1) #:param logic_is_available_p: [-] 1 = the machine is available in this timestep
    b.logic_must_run_p = Param (b.TIME_s, within=Binary, default=0) #:param logic_must_run_p: [-] 1 = the machine must be switched on
    b.logic_is_controllable_electricity_p = Param (b.TIME_s, within=Binary, default=1) #:param logic_is_controllable_p: [-] 1= the machine can be controlled by the EMS
    b.power_setpointElectricityOutput_p = Param (b.TIME_s, within=NonNegativeReals, default=0.0) #:param power_setpointElectricityOutput_p: [kW] if not controllable, this parameters set the electrical power of the machine
    
    b.logic_isAsmAllowed_p = Param(b.TIME_s, within=Binary, default=1) #:param logic_isAsmAllowed_p:# 1 = device is allowed to participate into ASM
    
    # .. section:: VARS
    b.power_fuelInput_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_fuelInput_v: [kW_fuel] Input of the GENSET,  in terms of mean power input in the timestep
    b.power_electricityOutput_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_electricityOutput_v:  [kW_el] Output of the GENSET, in terms of mean power output in the timestep
    
    b.power_actual_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_actual_v: [kWel] HELPER VAR - Actual output that can be supplied by the GENSET (e.g. 0 if is not on)
    
    b.logic_isOn_v = Var(b.TIME_s, within=Binary) #:param logic_isOn_v: [-] 1 = The machine is on during this timestep, otherwise 0
    b.logic_isStartingUp_v = Var(b.TIME_s, within=Binary) #:param logic_isStartingUp_v: [-] 1 = Machine is beginning start-up procedure during this timestep, otherwise 0
    b.logic_isShuttingDown_v = Var(b.TIME_s, within=Binary) #:param logic_isShuttingDown_v:  [-] 1 = Machine is at the start of shut-down procedure during this timestep, otherwise 0
    
    b.cost_operationMaintenance_v = Var(within=NonNegativeReals) #:param cost_operationMaintenance_v: [€] Total cost for O&M incurred by the Genset
    
    b.power_capacityRetentionUp_v = Var(b.TIME_s,within=Reals) #:param power_capacityRetentionUp_v: [kW_el] Capacity Retention upwards available for the GENSET
    b.power_capacityRetentionDown_v = Var(b.TIME_s,within=Reals) #:param power_capacityRetentionDown_v: [kW_el] Capacity Retention downwards available for the GENSET
    
    b.energy_NGforElectricity_v = Var(b.TIME_s,within=NonNegativeReals) #:param energy_NGforElectricity_v: [kWh] natural gas consumption for Energy Production
    
    b.cost_startUp_total_v = Var(within=NonNegativeReals)  #:param cost_startUp_total_v: [€] total costs incurred due to start-ups
    b.cost_shutDown_total_v = Var(within=NonNegativeReals)  #:param cost_shutDown_total_v: [€] total costs incurred due to shut-downs
    
    #CONSTRAINTS
    # CONTROLLABILITY: IF NOT CONTROLLABLE, I NEED TO PROVIDE A SET POINT # 
    @b.Constraint(b.TIME_s)
    def Genset_controllability(b,t):
        if b.logic_is_controllable_electricity_p[t] == 1:
            return Constraint.Skip
        else:
            return b.power_electricityOutput_v[t] == b.power_setpointElectricityOutput_p[t]*b.logic_is_available_p[t]
    
    @b.Constraint(b.TIME_s)
    def Genset_availability_p(b,t):
        if b.logic_is_available_p[t] == 0 :
           return b.logic_isOn_v[t] == 0
        else:
            return Constraint.Skip
    
    @b.Constraint(b.TIME_s)
    def Genset_actual_power(b,t):
        return b.power_actual_v[t] == b.logic_isOn_v[t]*b.power_nominal_p
        
    @b.Constraint(b.TIME_s)
    def Genset_production(b,t):
        # output = m*input + q
        return b.power_electricityOutput_v[t] == b.efficiency_slope_p*b.power_fuelInput_v[t]+b.efficiency_intercept_p*b.logic_isOn_v[t]
    
    # OUTPUT is constrained by technical max load and min load
    @b.Constraint(b.TIME_s)
    def Genset_production_LB(b,t):
        return b.power_electricityOutput_v[t] >= b.power_min_p*b.power_actual_v[t]
    
    @b.Constraint(b.TIME_s)
    def Genset_production_UB(b,t):
        return b.power_electricityOutput_v[t] <= b.power_max_p*b.power_actual_v[t]
    
    # OUTPUT is constrained by ramp limit, taking also in account start-ups and shut-downs 
    @b.Constraint(b.TIME_s)
    def Genset_rampup_startup_limit(b,t):
        if b.logic_is_available_p[t] == 1 :
            if t == b.TIME_s.first():
                prev_t = b.TIME_before_s.last()
                if b.timesteps_startUpDuration_p !=0: #slow machine
                    t_startUp=b.TIME_before_s[-b.timesteps_startUpDuration_p]
                    return b.power_electricityOutput_v[t]-b.power_electricityOutput_before_p[prev_t] <= b.power_rampUp_p*b.power_nominal_p*b.logic_isOn_before_p[prev_t] + b.logic_isStartingUp_before_p[t_startUp]*(b.power_startUp_p+b.power_min_p)*b.power_nominal_p     
                else: #fast machine
                    t_startUp = t
                    return b.power_electricityOutput_v[t]-b.power_electricityOutput_before_p[prev_t] <= b.power_rampUp_p*b.power_nominal_p*b.logic_isOn_before_p[prev_t] + b.logic_isStartingUp_v[t_startUp]*(b.power_startUp_p+b.power_min_p)*b.power_nominal_p     
            else:
                prev_t = b.TIME_s.prev(t)
                if t <= b.timesteps_startUpDuration_p and b.timesteps_startUpDuration_p != 0: #slow machine
                    t_startUp = t-b.timesteps_startUpDuration_p
                    return b.power_electricityOutput_v[t]-b.power_electricityOutput_v[prev_t] <= b.power_rampUp_p*b.power_actual_v[prev_t] + b.logic_isStartingUp_before_p[t_startUp]*(b.power_startUp_p+b.power_min_p)*b.power_nominal_p
                else: # slow machine with t>timesteps_startUpDuration & fast-machine
                    t_startUp = t-b.timesteps_startUpDuration_p
                    return b.power_electricityOutput_v[t]-b.power_electricityOutput_v[prev_t] <= b.power_rampUp_p*b.power_actual_v[prev_t] + b.logic_isStartingUp_v[t_startUp]*(b.power_startUp_p+b.power_min_p)*b.power_nominal_p
        else:
            return Constraint.Skip
        
    @b.Constraint(b.TIME_s)
    def Genset_rampdown_shutdown_limit(b,t):
        if b.logic_is_available_p[t] == 1 :
            if t == b.TIME_s.first():
                prev_t = b.TIME_before_s.last()
                return b.power_electricityOutput_before_p[prev_t]-b.power_electricityOutput_v[t] <= b.power_rampDown_p*b.power_actual_v[t] + b.logic_isShuttingDown_v[t]*(b.power_shutDown_p+b.power_min_p)*b.power_nominal_p
            else:
                prev_t = b.TIME_s.prev(t)
                return b.power_electricityOutput_v[prev_t]-b.power_electricityOutput_v[t] <= b.power_rampDown_p*b.power_actual_v[t] + b.logic_isShuttingDown_v[t]*(b.power_shutDown_p+b.power_min_p)*b.power_nominal_p
        else:
            return Constraint.Skip
        
    # Start-up and shut-down determine if the machine is on/off
    @b.Constraint(b.TIME_s)
    def Genset_startup_shutdown(b,t):
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
    
    # # If I'm starting up I cannot be shutting down
    @b.Constraint(b.TIME_s)
    def Genset_startup_shutdown_dicotomy(b,t):
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
    
    # # Minimum up-time and minimum downtime
    @b.Constraint(b.TIME_s)
    def Genset_minimum_uptime(b,t):
        if b.logic_is_available_p[t] == 1 :
            if t <= b.timesteps_minimumTimeOn_p+1:
                value = \
                    sum(b.logic_isOn_v[tau] for tau in range(1,t)) \
                        + sum(b.logic_isOn_before_p[tau_neg] for tau_neg in range(-b.timesteps_minimumTimeOn_p+t-1,1))    
            else:
                value = sum(b.logic_isOn_v[tau] for tau in range(t-b.timesteps_minimumTimeOn_p,t))
            
            return b.logic_isShuttingDown_v[t] <= value/b.timesteps_minimumTimeOn_p
        else:
            return Constraint.Skip
    
    @b.Constraint(b.TIME_s)
    def Genset_minimum_downtime(b,t):
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
        
    #Must run logics 
    @b.Constraint(b.TIME_s)
    def Genset_must_run(b,t):
        if b.logic_is_available_p[t] == 1 :
            return b.logic_isOn_v[t]>=b.logic_must_run_p[t]
        else:
            return Constraint.Skip
    
    #Cost maintenance calculation            
    @b.Constraint()
    def Genset_operationMaintenance_cost_calc(b):
        return b.cost_operationMaintenance_v == sum(b.cost_operationMaintenanceTimestep_p*b.logic_isOn_v[t] for t in b.TIME_s)
    
    #Constraint on the capacity retention
    @b.Constraint(b.TIME_s)
    def capacity_retention_up_calc(b,t):
        if b.logic_is_available_p[t] == 1 :
            prod_max = b.power_nominal_p.value*b.power_max_p.value*b.logic_isOn_v[t]
            return b.power_capacityRetentionUp_v[t] <= prod_max - b.power_electricityOutput_v[t]
        else:
            return Constraint.Skip
    
    @b.Constraint(b.TIME_s)
    def capacity_retention_down_calc(b,t):
        if b.logic_is_available_p[t] == 1 :
            prod_min = b.power_nominal_p.value*b.power_min_p.value*b.logic_isOn_v[t]
            return b.power_capacityRetentionDown_v[t] <= b.power_electricityOutput_v[t] - prod_min
        else:
            return Constraint.Skip
    
    @b.Constraint(b.TIME_s)
    def ASM_allowed_UP(b,t):
        if b.logic_isAsmAllowed_p[t] == 0:
            return b.power_capacityRetentionUp_v[t] == 0
        else:
            return Constraint.Skip
        
    @b.Constraint(b.TIME_s)
    def ASM_allowed_DOWN(b,t):
        if b.logic_isAsmAllowed_p[t] == 0:
            return b.power_capacityRetentionDown_v[t] == 0
        else:
            return Constraint.Skip
        
    @b.Constraint(b.TIME_s)
    def NGforElectricity_CALC(b,t):
        return b.energy_NGforElectricity_v[t] == b.power_fuelInput_v[t]*b.timestep_size_p
    
    @b.Constraint()
    def cost_startUp(b):
        return b.cost_startUp_total_v == sum(b.cost_startUp_p*b.logic_isStartingUp_v[t] for t in b.TIME_s)
    
    @b.Constraint()
    def cost_shutDown(b):
        return b.cost_shutDown_total_v == sum(b.cost_shutDown_p*b.logic_isShuttingDown_v[t] for t in b.TIME_s)
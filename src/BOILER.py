# -*- coding: utf-8 -*-
"""
BOILER model
"""

from pyomo.core import AbstractModel,Set,RangeSet,Param,Var,Constraint, Objective, minimize, NonNegativeIntegers,NonNegativeReals,Binary, Block, Reals
import pyomo.environ as pyo

def create_block(b,g):
    #SETS
    b.TIME_s = Set(initialize=b.model().TIME_s) # CRITICAL -> we're referencing the parent model within the child model, BUT at least is decoupled
    b.TIME_before_s = Set(initialize=b.model().TIME_before_s)
    
    @b.Param()
    def timesteps_before_p(b):
        return len(b.TIME_before_s)
    
    # .. section:: TIME-INDEPENDENT PARAMETERS
    b.power_nominal_p = Param(within=NonNegativeReals) #:param power_nominal_p: Nominal power of the BOILER (output) [kWel] 
    b.power_min_p = Param(within=NonNegativeReals) #:param power_min_p: Minimum Load for the BOILER, expressed as p.u. of power_nominal_p [pu]
    b.power_max_p = Param(within=NonNegativeReals) #:param Maximum Load for the BOILER, expressed as p.u. of power_nominal_p [pu]
    b.efficiency_slope_p = Param(within=Reals) #:param efficiency_slope_p: Slope term for part-load output calculation
    b.efficiency_intercept_p = Param(within=Reals) #:param efficiency_intercept_p: Intercept term for part-load output calculation
    b.power_rampUp_p = Param(within=NonNegativeReals) #:param power_rampUp_p: Max ramp-up in the timestep in terms of per-unit of output power [pu]
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
    
    # .. section:: INITIALIZATION PARAMETERS
    b.logic_isOn_before_p = Param(b.TIME_before_s, within=Binary)  #:param logic_isOn_before_p: [-] 1 = The machine is on during this timestep, otherwise 0; values outside optimization window;
    b.logic_isStartingUp_before_p = Param(b.TIME_before_s, within=Binary) #:param logic_isStartingUp_before_p: [-] 1 = Machine turned on during this timestep, otherwise 0
    b.logic_isShuttingDown_before_p = Param(b.TIME_before_s, within=Binary) #:param logic_isShuttingDown_before_p: [-] 1 = Machine shut down during this timestep, otherwise 0
    b.power_heatOutput_before_p = Param(b.TIME_before_s, within=NonNegativeReals) #:param power_electricityOutput_before_p: Output of the GENSET outside optimization window [kW_el]
    
    # .. section:: TIME-DEPENDENT PARAMETERS
    b.logic_is_available_p = Param(b.TIME_s, within=Binary, default=1) #:param logic_is_available_p: [-] 1 = the machine is available in this timestep
    b.logic_must_run_p = Param (b.TIME_s, within=Binary, default=0) #:param logic_must_run_p: [-] 1 = the machine must be switched on
    b.logic_isBoilerAssistActive_p = Param(b.TIME_s, within=Binary, default=0) #:param logic_isBoilerAssistActive_p: [-] Binary for logic Assistance of the Boiler 
    b.logic_is_controllable_heat_p = Param (b.TIME_s, within=Binary, default=1) #:param logic_is_controllable_heat_p: [-] 1= the machine can be controlled by the EMS
    b.power_setpointheatOutput_p = Param (b.TIME_s, within=NonNegativeReals, default=0.0) #:param power_setpointheatOutput_p: [kW] if not controllable, this parameters set the thermal power of the machine
    
    # .. section:: VARS
    b.power_fuelInput_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_fuelInput_v: [kW_fuel] Input of the BOILER, in terms of mean power input in the timestep
    b.power_heatOutput_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_heatOutput_v: [kW_th] Output of the BOILER, in terms of mean power output in the timestep
    
    b.power_actual_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_actual_v: [kWth] HELPER VAR - Actual output that can be supplied by the BOILER (e.g. 0 if is not on)
    
    b.logic_isOn_v = Var(b.TIME_s, within=Binary) #:param logic_isOn_v: [-] 1 = The machine is on during this timestep, otherwise 0
   
    b.logic_isStartingUp_v = Var(b.TIME_s, within=Binary) #:param logic_isStartingUp_v: [-] 1 = Machine is beginning start-up procedure during this timestep, otherwise 0
    b.logic_isShuttingDown_v = Var(b.TIME_s, within=Binary) #:param logic_isShuttingDown_v:  [-] 1 = Machine is at the start of shut-down procedure during this timestep, otherwise 0
    
    b.cost_operationMaintenance_v = Var(within=NonNegativeReals) #:param cost_operationMaintenance_v: [€] Total cost for O&M incurred by the BOILER
    
    
    #CONSTRAINTS
    @b.Constraint(b.TIME_s)
    def Boiler_availability_p(b,t):
        if b.logic_is_available_p[t] == 0 :
           return b.logic_isOn_v[t] == 0
        else:
            return Constraint.Skip
    
    @b.Constraint(b.TIME_s)
    def Boiler_actual_power(b,t):
        return b.power_actual_v[t] == b.logic_isOn_v[t]*b.power_nominal_p   
    
    @b.Constraint(b.TIME_s)
    def Boiler_production(b,t):
        # output = m*input + q
        return b.power_heatOutput_v[t] == b.efficiency_slope_p*b.power_fuelInput_v[t]+b.efficiency_intercept_p*b.logic_isOn_v[t]
        
        
    # OUTPUT is constrained by technical max load and min load
    @b.Constraint(b.TIME_s)
    def Boiler_production_LB(b,t):
        return b.power_heatOutput_v[t] >= b.power_min_p*b.power_actual_v[t]
    
    @b.Constraint(b.TIME_s)
    def Boiler_production_UB(b,t):
        return b.power_heatOutput_v[t] <= b.power_max_p*b.power_actual_v[t]
            
    # OUTPUT is constrained by ramp limit, taking also in account start-ups and shut-downs 
    @b.Constraint(b.TIME_s)
    def Boiler_rampup_startup_limit(b,t):
        if b.logic_is_available_p[t] == 1 :
            if t == b.TIME_s.first():
                prev_t = b.TIME_before_s.last()
                if b.timesteps_startUpDuration_p !=0: #slow machine
                    t_startUp=b.TIME_before_s[-b.timesteps_startUpDuration_p]
                    return b.power_heatOutput_v[t]-b.power_heatOutput_before_p[prev_t] <= b.power_rampUp_p*b.power_nominal_p*b.logic_isOn_before_p[prev_t] + b.logic_isStartingUp_before_p[t_startUp]*(b.power_startUp_p+b.power_min_p)*b.power_nominal_p     
                else: #fast machine
                    t_startUp = t
                    return b.power_heatOutput_v[t]-b.power_heatOutput_before_p[prev_t] <= b.power_rampUp_p*b.power_nominal_p*b.logic_isOn_before_p[prev_t] + b.logic_isStartingUp_v[t_startUp]*(b.power_startUp_p+b.power_min_p)*b.power_nominal_p     
            else:
                prev_t = b.TIME_s.prev(t)
                if t <= b.timesteps_startUpDuration_p and b.timesteps_startUpDuration_p != 0: #slow machine
                    t_startUp = t-b.timesteps_startUpDuration_p
                    return b.power_heatOutput_v[t]-b.power_heatOutput_v[prev_t] <= b.power_rampUp_p*b.power_actual_v[prev_t] + b.logic_isStartingUp_before_p[t_startUp]*(b.power_startUp_p+b.power_min_p)*b.power_nominal_p
                else: # slow machine with t>timesteps_startUpDuration & fast-machine
                    t_startUp = t-b.timesteps_startUpDuration_p
                    return b.power_heatOutput_v[t]-b.power_heatOutput_v[prev_t] <= b.power_rampUp_p*b.power_actual_v[prev_t] + b.logic_isStartingUp_v[t_startUp]*(b.power_startUp_p+b.power_min_p)*b.power_nominal_p
        else:
            return Constraint.Skip        
        
    @b.Constraint(b.TIME_s)
    def Boiler_rampdown_shutdown_limit(b,t):
        if b.logic_is_available_p[t] == 1 :
            if t == b.TIME_s.first():
                prev_t = b.TIME_before_s.last()
                return b.power_heatOutput_before_p[prev_t]-b.power_heatOutput_v[t] <= b.power_rampDown_p*b.power_actual_v[t] + b.logic_isShuttingDown_v[t]*(b.power_shutDown_p+b.power_min_p)*b.power_nominal_p
            else:
                prev_t = b.TIME_s.prev(t)
                return b.power_heatOutput_v[prev_t]-b.power_heatOutput_v[t] <= b.power_rampDown_p*b.power_actual_v[t] + b.logic_isShuttingDown_v[t]*(b.power_shutDown_p+b.power_min_p)*b.power_nominal_p
        else:
            return Constraint.Skip        
        
    # Start-up and shut-down determine if the machine is on/off
    @b.Constraint(b.TIME_s)
    def Boiler_startup_shutdown(b,t):
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
    def Boiler_startup_shutdown_dicotomy(b,t):
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
    def Boiler_minimum_uptime(b,t):
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
    def Boiler_minimum_downtime(b,t):
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
    def Boiler_must_run(b,t):
        if b.logic_is_available_p[t] == 1 :
            return b.logic_isOn_v[t]>=b.logic_must_run_p[t]
        else:
            return Constraint.Skip
    
    @b.Constraint()
    def Boiler_operationMaintenance_cost_calc(b):
        return b.cost_operationMaintenance_v == sum(b.cost_operationMaintenanceTimestep_p*b.logic_isOn_v[t] for t in b.TIME_s)
    
    # CONTROLLABILITY: IF NOT CONTROLLABLE, I NEED TO PROVIDE A SET POINT # 
    @b.Constraint(b.TIME_s)
    def Boiler_controllability(b,t):
        if b.logic_is_controllable_heat_p[t] == 1:
            return Constraint.Skip
        else:
            return b.power_heatOutput_v[t] == b.power_setpointheatOutput_p[t]*b.logic_is_available_p[t]
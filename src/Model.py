"""
EMS model
"""

from pyomo.core import AbstractModel, Set, RangeSet, Param, Var, Block, Constraint, NonNegativeIntegers, NonNegativeReals, Reals, Binary
# import pyomo.environ as pyo

#import each library here
import src.GENSET as genset_lib
import src.POD as pod_lib
import src.PDR as pdr_lib
import src.PV as pv_lib
import src.EL_LOAD as el_load_lib
import src.TH_LOAD as th_load_lib
import src.BOILER as boiler_lib
import src.COGEN as cogen_lib
import src.BESS as bess_lib
# import BESS_SW as bess_lib
import src.EV as ev_lib

mod = AbstractModel(name="EMS")

mod.logic_schedulingReschedulingSelection_p = Param(within=NonNegativeIntegers) #: param logic_schedulingReschedulingSelection_p: [0] is scheduling , [1] is rescheduling


# .. section:: Parameters for the creation of the TIME set
mod.timesteps_p = Param(within=NonNegativeIntegers) #:param timesteps_p: number of timesteps in optimization horizon
mod.timesteps_before_p = Param(within=NonNegativeIntegers, mutable=False) #:param timesteps_before_p: number of timesteps before the optimization horizon required for initialization
mod.TIME_s = RangeSet(mod.timesteps_p) # [1,2,3,...]
mod.TIME_before_s = RangeSet(-mod.timesteps_before_p+1,0) # [...,-2,-1,0]
mod.timestep_size_p = Param(within=NonNegativeReals) #:param timestep_size_p: [h] dimension of the timestep

# .. section:: Parameters
mod.bigM_p = Param(within=NonNegativeReals, default = 1000000) #:param bigM_p: [-] big number
mod.temperature_external_p=Param(mod.TIME_s, within=Reals) #:param temperature_external_p: external temperature in the site
   
#...section:: Creation of the set to populate technology blocks
mod.GENSET_s = Set()
mod.BOILER_s = Set()
mod.COGEN_s = Set()
mod.POD_s = Set()
mod.PDR_s = Set()
mod.PV_s = Set()
mod.BESS_s = Set()
mod.EV_s = Set()
mod.EL_LOAD_s = Set()
mod.EL_CIRCUIT_s = Set()
mod.NG_CIRCUIT_s = Set()
mod.TH_CIRCUIT_s = Set()
mod.TH_LOAD_s = Set()


#...section:: Creation of the Technology blocks indexed on global sets
mod.GENSET_b = Block(mod.GENSET_s, rule=genset_lib.create_block)
mod.BOILER_b = Block(mod.BOILER_s, rule=boiler_lib.create_block)
mod.COGEN_b  = Block(mod.COGEN_s, rule=cogen_lib.create_block)
mod.POD_b = Block(mod.POD_s, rule=pod_lib.create_block)
mod.PDR_b = Block(mod.PDR_s, rule=pdr_lib.create_block)
mod.PV_b = Block(mod.PV_s, rule=pv_lib.create_block)
mod.BESS_b = Block(mod.BESS_s, rule=bess_lib.create_block)
mod.EV_b = Block(mod.EV_s, rule=ev_lib.create_block)
mod.EL_LOAD_b = Block(mod.EL_LOAD_s, rule=el_load_lib.create_block) 
mod.TH_LOAD_b = Block(mod.TH_LOAD_s, rule=th_load_lib.create_block)

#...section:: Variables for objective function calculation
mod.OPEX = Var() #:param OPEX: Variable - Operative Expenditures (OPEX) of the problem, which is the objective function
mod.penalty_withdrawn_v = Var(within=NonNegativeReals) #:param penalty_withdrawn_v: penalty to achieve track mode of minimal withdrawn 
mod.penalty_slack_v = Var(within=NonNegativeReals) #:param penalty_slack_v: penalty for the usage of slack variables in constraints
mod.penalty_imbalance_v = Var(within=NonNegativeReals) #:param penalty_imbalance_v: penalty for imbalance in constraints
 
#...section:: EL Circuit block
# HP: circuits must be created by the modeler, they're not reusable blocks
@mod.Block(mod.EL_CIRCUIT_s)
def EL_CIRCUIT_b(b,c):
        mod = b.model()
        b.TIME_s = Set(initialize=mod.TIME_s)
        b.timestep_size_p = Param(initialize=mod.timestep_size_p)
        
        #...section:: Connected machines are handled using SETS (modeler adds sets and corresponding initialization in data)
        b.CONNECTED_GENSET_s = Set(within=mod.GENSET_s)
        b.CONNECTED_COGEN_s = Set(within=mod.COGEN_s)
        b.CONNECTED_POD_s = Set(within=mod.POD_s)
        b.CONNECTED_PV_s = Set(within=mod.PV_s)
        b.CONNECTED_BESS_s = Set(within=mod.BESS_s)
        b.CONNECTED_EV_s = Set(within = mod.EV_s)
        b.CONNECTED_EL_LOAD_s = Set(within=mod.EL_LOAD_s)
              
        b.power_capacityRetentionUp_p = Param(b.TIME_s, within=NonNegativeReals, default=0) #:param power_capacityRetentionUp_v: [kW_el] Capacity Retention upwards available 
        b.power_capacityRetentionDown_p = Param(b.TIME_s, within=NonNegativeReals, default=0) #:param power_capacityRetentionDown_v: [kW_el] Capacity Retention downwards available 
        
        #.. section:: Variables of the Electric circuit
        b.power_totalProduction_v = Var(b.TIME_s, within=NonNegativeReals) #:param power_totalProduction_v: [kW_el] total electrical production of the micro-grid

        #Create new variables for actual CR
        b.power_capacityRetentionUp_actual_v = Var(b.TIME_s, within=Reals) #:param power_capacityRetentionUp_actual_v: [kW_el] Actual Capacity Retention upwards available after subtracting BDEs
        b.power_capacityRetentionDown_actual_v = Var(b.TIME_s, within=Reals) #:param power_capacityRetentionDown_actual_v: [kW_el] Actual Capacity Retention downwards available after subtracting BDEs


        @b.Constraint(b.TIME_s)
        def power_capacityRetentionUp_actual_calc(b,t):
            if mod.logic_schedulingReschedulingSelection_p == 0:
                #SCHEDULING = CR is the one given in the param
                return b.power_capacityRetentionUp_actual_v[t] == b.power_capacityRetentionUp_p[t]
            else:
                #RESCHEDULING = subtract BDE from param
                return b.power_capacityRetentionUp_actual_v[t] == b.power_capacityRetentionUp_p[t] - sum(mod.POD_b[g].BDE_Up_v[t] for g in b.CONNECTED_POD_s)
    
        @b.Constraint(b.TIME_s)
        def power_capacityRetentionDown_actual_calc(b,t):
            if mod.logic_schedulingReschedulingSelection_p == 0:
                #SCHEDULING = CR is the one given in the param
                return b.power_capacityRetentionDown_actual_v[t] == b.power_capacityRetentionDown_p[t]
            else:
                #RESCHEDULING = subtract BDE from param
                return b.power_capacityRetentionDown_actual_v[t] == b.power_capacityRetentionDown_p[t] - sum(mod.POD_b[g].BDE_Down_v[t] for g in b.CONNECTED_POD_s)
 
    
        # link needed variables to connected POD
        @b.Constraint(b.CONNECTED_POD_s,b.TIME_s)
        def powerConsumptionLink(b,u,t):
            #in this case, the only electricity consumer is the electricity load
            value = sum(mod.EL_LOAD_b[l].power_electricityDemand_p[t] for l in b.CONNECTED_EL_LOAD_s)
            return mod.POD_b[u].power_electricityConsumption_v[t] == value
        
        # pass temperature to the BESS
        @b.Constraint(b.CONNECTED_BESS_s,b.TIME_s)
        def temperatureLink(b,u,t):
            return mod.BESS_b[u].temperature_external_v[t] == mod.temperature_external_p[t]
        
        @b.Constraint(b.TIME_s)
        def totalProduction_calc(b,t):   
            return b.power_totalProduction_v[t] == \
                + sum(mod.GENSET_b[g].power_electricityOutput_v[t] for g in b.CONNECTED_GENSET_s) \
                + sum(mod.COGEN_b[u].power_electricityOutput_v[t] for u in b.CONNECTED_COGEN_s) \
                + sum(mod.PV_b[p].power_electricityProduction_p[t] for p in b.CONNECTED_PV_s) \
                + sum(mod.BESS_b[e].power_dischargeAC_v[t]*mod.BESS_b[e].power_nominal_p for e in b.CONNECTED_BESS_s)
        
        @b.Constraint(b.TIME_s)
        def el_balance(b,t):
            EL_IN = sum(mod.POD_b[p].power_electricityWithdrawn_v[t] for p in b.CONNECTED_POD_s) + b.power_totalProduction_v[t]
            EL_OUT = \
                sum(mod.EL_LOAD_b[l].power_electricityDemand_p[t] for l in b.CONNECTED_EL_LOAD_s) \
              + sum(mod.POD_b[p].power_electricityInjected_v[t] for p in b.CONNECTED_POD_s) \
              + sum(mod.BESS_b[e].power_chargeAC_v[t]*mod.BESS_b[e].power_nominal_p for e in b.CONNECTED_BESS_s) \
              + sum(mod.BESS_b[e].power_aux_v[t] for e in b.CONNECTED_BESS_s) \
              + sum(mod.EV_b[v].power_Charged_v[t] for v in b.CONNECTED_EV_s)
            return EL_IN == EL_OUT
        
        # Calculate Balancing capacity available to the circuit
        @b.Constraint(b.TIME_s)
        def capacityRetentionUp_calc(b,t):
            return b.power_capacityRetentionUp_actual_v[t] == \
                sum(mod.GENSET_b[g].power_capacityRetentionUp_v[t] for g in b.CONNECTED_GENSET_s) \
              + sum(mod.COGEN_b[u].power_capacityRetentionUp_v[t] for u in b.CONNECTED_COGEN_s) \
              + sum(mod.BESS_b[e].power_capacityRetentionUp_v[t] for e in b.CONNECTED_BESS_s)    
                
        @b.Constraint(b.TIME_s)
        def capacityRetentionDown_calc(b,t):
            return b.power_capacityRetentionDown_actual_v[t] == \
                sum(mod.GENSET_b[g].power_capacityRetentionDown_v[t] for g in b.CONNECTED_GENSET_s) \
              + sum(mod.COGEN_b[u].power_capacityRetentionDown_v[t] for u in b.CONNECTED_COGEN_s) \
              + sum(mod.BESS_b[e].power_capacityRetentionDown_v[t] for e in b.CONNECTED_BESS_s) 

#...section:: Natural Gas Circuit      
@mod.Block(mod.NG_CIRCUIT_s)
def NG_CIRCUIT_b(b,c):
    mod = b.model()
    b.TIME_s = Set(initialize=mod.TIME_s)
    
    # Sets for connected machines
    b.CONNECTED_GENSET_s = Set(within=mod.GENSET_s)
    b.CONNECTED_COGEN_s = Set(within=mod.COGEN_s)
    b.CONNECTED_PDR_s = Set(within=mod.PDR_s)
    b.CONNECTED_BOILER_s = Set(within=mod.BOILER_s)  
    
    #.. section:: Variables of the Natural Gas circuit
    b.energy_NGforElectricity_v = Var(mod.TIME_s,within=NonNegativeReals) #:param energy_NGforElectricity_v: [kWh_fuel] total natural gas consumed for electricity production 
    b.energy_NGtotalConsumption_v = Var(mod.TIME_s, within=NonNegativeReals) #:param energy_NGtotalConsumption_v: [kWh_fuel] Helper variable to aggregate different technologies
    
    @b.Constraint(mod.TIME_s)
    def totalConsumption_calc(b,t):
        return b.energy_NGtotalConsumption_v[t] == mod.timestep_size_p*( \
            sum(mod.GENSET_b[g].power_fuelInput_v[t] for g in b.CONNECTED_GENSET_s) \
          + sum(mod.COGEN_b[u].power_fuelInput_v[t] for u in b.CONNECTED_COGEN_s) \
          + sum(mod.BOILER_b[u].power_fuelInput_v[t] for u in b.CONNECTED_BOILER_s))
    
    @b.Constraint(mod.TIME_s)
    def NG_balance(b,t): 
        return sum(mod.PDR_b[u].smc_withdrawn_v[t]*mod.PDR_b[u].LHV_p for u in b.CONNECTED_PDR_s) == b.energy_NGtotalConsumption_v[t]
    
    # calculate fuel_energy used for electricity production
    @b.Constraint(mod.TIME_s)
    def fuelForElectricity_calc(b,t):
        
        # kWh_fuel = kW_fuel * timestep_size
        value = sum(mod.GENSET_b[g].energy_NGforElectricity_v[t] for g in b.CONNECTED_GENSET_s) \
              + sum(mod.COGEN_b[u].energy_NGforElectricity_v[t] for u in b.CONNECTED_COGEN_s) 
        return b.energy_NGforElectricity_v[t] == value
    
    # link fuel used for electricity production to corresponing variable in PDR
    @b.Constraint(b.CONNECTED_PDR_s,mod.TIME_s)
    def fuelForElectricity_link(b,u,t):
        return mod.PDR_b[u].smc_ElectricityProduction_v[t] == b.energy_NGforElectricity_v[t]/mod.PDR_b[u].LHV_p
      
#...section:: Thermal Circuit     
@mod.Block(mod.TH_CIRCUIT_s)
def TH_CIRCUIT_b(b,c):
    mod = b.model()
    b.TIME_s = Set(initialize=mod.TIME_s)
    
    # Sets for connected machines
    b.CONNECTED_BOILER_s = Set(within=mod.BOILER_s)
    b.CONNECTED_COGEN_s = Set(within=mod.COGEN_s)
    b.CONNECTED_TH_LOAD_s = Set(within=mod.TH_LOAD_s)
    b.ORDERED_BOILER_s = Set(mod.TIME_s, within=b.CONNECTED_BOILER_s)
    
    #.. section:: Time-dependend parameters
    b.logic_isBoilerRotationActive_p = Param(mod.TIME_s, within=Binary, default=0) #:param logic_isBoilerRotationActive_p: [-] Binary for logic Rotation of the Boiler 
    b.logic_isBoilerForceMaxActive_p = Param(mod.TIME_s, within=Binary, default=0) #:param logic_isBoilerForceMaxActive_p: [-] Binary for logic Force Max of the Boiler
    
    #.. section:: Variables
    b.power_heatTotalProduction_v = Var(mod.TIME_s, within=NonNegativeReals) #:param power_heatTotalProduction_v:  HELPER var - calculate total production from different technologies
    
    @b.Constraint(mod.TIME_s)
    def Heat_production_calc(b,t):
        return b.power_heatTotalProduction_v[t] == \
            sum(mod.BOILER_b[u].power_heatOutput_v[t] for u in b.CONNECTED_BOILER_s) \
          + sum(mod.COGEN_b[u].power_heatOutput_v[t] for u in b.CONNECTED_COGEN_s)
    
    @b.Constraint(mod.TIME_s)
    def Thermal_balance(b,t): 
        return sum(mod.TH_LOAD_b[l].power_heatDemand_p[t] for l in b.CONNECTED_TH_LOAD_s) <= b.power_heatTotalProduction_v[t]
     
    # Constraint on Boiler: Can switch on only if at least one cogen is on     
    @b.Constraint(b.CONNECTED_BOILER_s, mod.TIME_s)
    def Boiler_Assistance(b,u,t):
        if mod.BOILER_b[u].logic_isBoilerAssistActive_p[t] == 1\
        and mod.BOILER_b[u].logic_must_run_p[t] == 0 :
            value = sum(mod.COGEN_b[g].logic_isOn_v[t] for g in b.CONNECTED_COGEN_s) 
            return mod.BOILER_b[u].logic_isOn_v[t] <= value
        else:
            return Constraint.Skip
      
    # Constraint on Boiler: forces boiler to turn on in a sequence set in a subset called "ORDERED_BOILER_s"
    @b.Constraint(b.CONNECTED_BOILER_s, mod.TIME_s)
    def Boiler_rotation (b,u,t):
        if mod.BOILER_b[u].logic_is_controllable_heat_p[t] == 1 \
           and b.logic_isBoilerRotationActive_p[t] == 1\
           and mod.BOILER_b[u].logic_must_run_p[t] == 0 : # the boiler has to be controllable, available and not in must run
            if u == b.ORDERED_BOILER_s[t].first():  #skip the first boiler
                return Constraint.Skip 
            else:
                prev = b.ORDERED_BOILER_s[t].prev(u)  
                found = 'no'
                while mod.BOILER_b[prev].logic_is_available_p[t] == 0 and prev > b.ORDERED_BOILER_s[t].first():  #look for one previous boiler that is available 
                    prev = b.ORDERED_BOILER_s[t].prev(prev)               
                if mod.BOILER_b[prev].logic_is_available_p[t] == 1 :  #if there is one available set the helper variable found to be yes
                    found = 'yes'
                if found == 'yes':
                    return mod.BOILER_b[u].logic_isOn_v[t] <= mod.BOILER_b[prev].logic_isOn_v[t]
                else: 
                    return Constraint.Skip
        else:
            return Constraint.Skip 
        
    # Constraint on Boiler: force boiler to turn on only if the priority boiler is at 100%
    @b.Constraint(b.CONNECTED_BOILER_s, mod.TIME_s)
    def Boiler_forceMAX (b,u,t):
        if mod.BOILER_b[u].logic_is_controllable_heat_p[t] == 1\
          and b.logic_isBoilerForceMaxActive_p[t] == 1\
          and mod.BOILER_b[u].logic_must_run_p[t] == 0 : # the boiler has to be controllable, available and not in must run
            if u == b.ORDERED_BOILER_s[t].first():  #skip the first boiler
                return Constraint.Skip 
            else: 
                prev = b.ORDERED_BOILER_s[t].prev(u)
                found = 'no'
                while mod.BOILER_b[prev].logic_is_available_p[t] == 0 and prev > b.ORDERED_BOILER_s[t].first():
                    prev = b.ORDERED_BOILER_s[t].prev(prev) 
                if mod.BOILER_b[prev].logic_is_available_p[t] == 1 : #if there is one available set the helper variable found to be yes
                    found='yes'
                if found == 'yes':
                    load_prev = mod.BOILER_b[prev].power_heatOutput_v[t]/mod.BOILER_b[prev].power_nominal_p
                    return  mod.BOILER_b[u].logic_isOn_v[t] <= load_prev   #can't switch on if load of the previous boiler is not 1
                else:
                    return Constraint.Skip
        else:
            return Constraint.Skip 
        
        
      
#...section:: Capacity retention block

@mod.Block()
def FLEX_b(b):
    mod = b.model()
    b.TIME_s = Set(initialize=mod.TIME_s)
    #.. section:: Variables of the Capacity retention circuit
    
    b.BDE_Up_p=Param(b.TIME_s,within=NonNegativeReals, default=0.0) #:param BDE_UP_p: [kWel] =1 BDE upward
    b.BDE_Down_p=Param(b.TIME_s,within=NonNegativeReals, default = 0.0) #:param BDE_DOWN_p: [kWel]  =1 BDE downward
    
    b.power_capacityRetentionUp_v = Var(b.TIME_s, within=Reals) #:param power_capacityRetentionUp_p: [kWel] Capacity Retention requested - Upwards
    b.power_capacityRetentionDown_v = Var(b.TIME_s, within=Reals) #:param power_capacityRetentionDown_p: [kWel] Capacity Retention requested - Downwards
    
    @b.Constraint(b.TIME_s)
    def Total_Capacity_Retention_Up(b,t):
        return b.power_capacityRetentionUp_v[t] == sum(mod.EL_CIRCUIT_b[p].power_capacityRetentionUp_actual_v[t] for p in mod.EL_CIRCUIT_s)
    
    @b.Constraint(b.TIME_s)
    def Total_Capacity_Retention_Down(b,t):
        return b.power_capacityRetentionDown_v[t] == sum(mod.EL_CIRCUIT_b[p].power_capacityRetentionDown_actual_v[t] for p in mod.EL_CIRCUIT_s)    
     
    @b.Constraint(b.TIME_s)
    def BDE_Up_link(b,t):
        if mod.logic_schedulingReschedulingSelection_p == 1:
            return b.BDE_Up_p[t] == sum(mod.POD_b[g].BDE_Up_v[t] for g in mod.POD_s)
        else:
            return Constraint.Skip
    
    @b.Constraint(b.TIME_s)
    def BDE_Down_link(b,t):
        if mod.logic_schedulingReschedulingSelection_p == 1:
            return b.BDE_Down_p[t] == sum(mod.POD_b[g].BDE_Down_v[t] for g in mod.POD_s)
        else:
            return Constraint.Skip
   
# Constraint on the tracking mode of COGEN = "TRACK MODE THERMAL"
# Constraint on the COGEN Tracking mode = COGEN follows thermal load 
  
@mod.Constraint(mod.EL_CIRCUIT_s,mod.TIME_s)
def EL_tracking(mod,c,t):
    if any(mod.COGEN_b[u].logic_is_trackmode_on_p[t] == 1 and\
       mod.COGEN_b[u].logic_is_available_p[t] == 1 and\
       mod.COGEN_b[u].logic_is_controllable_electricity_p[t] == 1 and\
       mod.COGEN_b[u].logic_is_controllable_heat_p[t] == 1 \
       for u in mod.EL_CIRCUIT_b[c].CONNECTED_COGEN_s): #initialize the constraint only if there is at least one cogen available, controllable and whose track mode is EL or MAX
        total_EL_load = sum(mod.EL_LOAD_b[l].power_electricityDemand_p[t]\
                        for l in mod.EL_CIRCUIT_b[c].CONNECTED_EL_LOAD_s)\
                        - sum (mod.PV_b[p].power_electricityProduction_p[t]\
                        for p in mod.EL_CIRCUIT_b[c].CONNECTED_PV_s) #calculate the electric load of the circuit - the production power of the photovoltaic panels
        total_TH_load = 0
        for circuit in mod.TH_CIRCUIT_s:  #calculate the thermal load by sum of the thermal load of the connected cogen in el mode
            for u in mod.EL_CIRCUIT_b[c].CONNECTED_COGEN_s:
                if u in mod.TH_CIRCUIT_b[circuit].CONNECTED_COGEN_s:            
                    total_TH_load += sum(mod.TH_LOAD_b[a].power_heatDemand_p[t]\
                    for a in mod.TH_CIRCUIT_b[circuit].CONNECTED_TH_LOAD_s)
                    break
        if any ((mod.COGEN_b[u].track_mode_p[t] == 1 or\
           (mod.COGEN_b[u].track_mode_p[t] == 3 and total_EL_load >= total_TH_load)) and\
           mod.COGEN_b[u].logic_is_available_p[t] == 1 and\
           mod.COGEN_b[u].logic_is_controllable_electricity_p[t] == 1 and\
           mod.COGEN_b[u].logic_is_controllable_heat_p[t] == 1\
           for u in mod.EL_CIRCUIT_b[c].CONNECTED_COGEN_s):
            min_production = min(mod.COGEN_b[u].power_electricityMin_p*mod.COGEN_b[u].power_electricityNominal_p\
                             for u in mod.EL_CIRCUIT_b[c].CONNECTED_COGEN_s\
                             if mod.COGEN_b[u].logic_is_available_p[t] == 1 and\
                                mod.COGEN_b[u].logic_is_controllable_electricity_p[t] == 1 and\
                                mod.COGEN_b[u].logic_is_controllable_heat_p[t] == 1 and\
                                mod.COGEN_b[u].logic_is_trackmode_on_p[t] == 1 and\
                                (mod.COGEN_b[u].track_mode_p[t] == 1 or\
                                (mod.COGEN_b[u].track_mode_p[t] == 3 and total_EL_load >= total_TH_load))) #the minimum production of the cogens is the minimum load of 1 cogen whose available, controllable and in EL_tracking mode
            max_production = sum(mod.COGEN_b[u].power_electricityMax_p*mod.COGEN_b[u].power_electricityNominal_p\
                             for u in mod.EL_CIRCUIT_b[c].CONNECTED_COGEN_s \
                             if mod.COGEN_b[u].logic_is_available_p[t] == 1 and\
                                mod.COGEN_b[u].logic_is_controllable_electricity_p[t] == 1 and\
                                mod.COGEN_b[u].logic_is_controllable_heat_p[t] == 1 and\
                                mod.COGEN_b[u].logic_is_trackmode_on_p[t] == 1 and\
                               (mod.COGEN_b[u].track_mode_p[t] == 1 or\
                               (mod.COGEN_b[u].track_mode_p[t] == 3 and total_EL_load >= total_TH_load)))  # the maximum production is the sum of the maximum load of all available, controllable and in EL_tracking mode cogens
            if total_EL_load == 0: #is there is no el_load skip constraint
                return Constraint.Skip
            elif 0 < total_EL_load <= min_production: #if the electric load is less than the minimum production of the cogens set the sum of all available, controllable and in EL_tracking cogens at minimum
                value=min_production
            elif min_production < total_EL_load < max_production: #if the electric load is less than the maximum production of the cogens set the sum of all available, controllable and in EL_tracking cogens at the electric load
                value= total_EL_load                     
            else: #if the electric load is more than the maximum production of the cogens set the sum of all available, controllable and in EL_tracking cogens at maximum
                value = max_production
            return sum(mod.COGEN_b[u].power_electricityOutput_v[t]\
                   for u in mod.EL_CIRCUIT_b[c].CONNECTED_COGEN_s\
                   if mod.COGEN_b[u].logic_is_available_p[t] == 1 and\
                       mod.COGEN_b[u].logic_is_controllable_electricity_p[t] == 1 and\
                       mod.COGEN_b[u].logic_is_controllable_heat_p[t] == 1 and\
                      mod.COGEN_b[u].logic_is_trackmode_on_p[t] == 1 and\
                      (mod.COGEN_b[u].track_mode_p[t] == 1 or\
                      (mod.COGEN_b[u].track_mode_p[t] == 3 and total_EL_load >= total_TH_load))) == value
        else:
            return Constraint.Skip
    else:
        return Constraint.Skip
        
        
@mod.Constraint(mod.TH_CIRCUIT_s,mod.TIME_s)
def TH_tracking(mod,c,t):
    if any(mod.COGEN_b[u].logic_is_trackmode_on_p[t] == 1 and\
           mod.COGEN_b[u].logic_is_available_p[t] == 1 and\
           mod.COGEN_b[u].logic_is_controllable_electricity_p[t] == 1 and\
           mod.COGEN_b[u].logic_is_controllable_heat_p[t] == 1\
           for u in mod.TH_CIRCUIT_b[c].CONNECTED_COGEN_s):
        total_TH_load = sum(mod.TH_LOAD_b[l].power_heatDemand_p[t]\
                        for l in mod.TH_CIRCUIT_b[c].CONNECTED_TH_LOAD_s)
        total_EL_load = 0
        for circuit in mod.EL_CIRCUIT_s:
            for u in mod.TH_CIRCUIT_b[c].CONNECTED_COGEN_s:
                if u in mod.EL_CIRCUIT_b[circuit].CONNECTED_COGEN_s:            
                    total_EL_load += sum(mod.EL_LOAD_b[a].power_electricityDemand_p[t]\
                                     for a in mod.EL_CIRCUIT_b[circuit].CONNECTED_EL_LOAD_s)\
                                    - sum (mod.PV_b[g].power_electricityProduction_p[t]\
                                    for g in mod.EL_CIRCUIT_b[circuit].CONNECTED_PV_s)
                    break
        if any( mod.COGEN_b[u].track_mode_p[t] == 2 or\
              (mod.COGEN_b[u].track_mode_p[t] == 3 and total_EL_load < total_TH_load ) \
              for u in mod.TH_CIRCUIT_b[c].CONNECTED_COGEN_s):
            min_production = min(mod.COGEN_b[u].power_heatMin_p*mod.COGEN_b[u].power_heatNominal_p for u in mod.TH_CIRCUIT_b[c].CONNECTED_COGEN_s \
                             if mod.COGEN_b[u].logic_is_available_p[t] == 1 and\
                                mod.COGEN_b[u].logic_is_controllable_electricity_p[t] == 1 and\
                                mod.COGEN_b[u].logic_is_controllable_heat_p[t] == 1 and\
                                mod.COGEN_b[u].logic_is_trackmode_on_p[t] == 1 and \
                                (mod.COGEN_b[u].track_mode_p[t] == 2 or\
                                (mod.COGEN_b[u].track_mode_p[t] == 3 and total_EL_load < total_TH_load))) 
            max_production = sum(mod.COGEN_b[u].power_heatMax_p*mod.COGEN_b[u].power_heatNominal_p for u in mod.TH_CIRCUIT_b[c].CONNECTED_COGEN_s\
                             if mod.COGEN_b[u].logic_is_available_p[t] == 1 and\
                                mod.COGEN_b[u].logic_is_controllable_electricity_p[t] == 1 and\
                                mod.COGEN_b[u].logic_is_controllable_heat_p[t] == 1 and\
                                mod.COGEN_b[u].logic_is_trackmode_on_p[t] == 1 and\
                                (mod.COGEN_b[u].track_mode_p[t] == 2 or\
                                (mod.COGEN_b[u].track_mode_p[t] == 3 and total_EL_load < total_TH_load)) )      
            if total_TH_load == 0:
                return Constraint.Skip
            elif 0 < total_TH_load <= min_production:
                value=min_production
            elif min_production < total_TH_load < max_production: 
                value= total_TH_load                     
            else:
                value = max_production 
            return sum(mod.COGEN_b[u].power_heatOutput_v[t] for u in mod.TH_CIRCUIT_b[c].CONNECTED_COGEN_s\
                   if mod.COGEN_b[u].logic_is_available_p[t] == 1 and\
                      mod.COGEN_b[u].logic_is_controllable_electricity_p[t] == 1 and\
                      mod.COGEN_b[u].logic_is_controllable_heat_p[t] == 1 and\
                      mod.COGEN_b[u].logic_is_trackmode_on_p[t] == 1 and\
                      (mod.COGEN_b[u].track_mode_p[t] == 2 or \
                      (mod.COGEN_b[u].track_mode_p[t] == 3 and total_EL_load < total_TH_load ))) == value
        else:
            return Constraint.Skip  
    else:
        return Constraint.Skip  
    
#OPEX = electricity costs per circuit + natural gas costs per circuit + O&M per unit    
#Calculate Operative Expenditures (OPEX) of the problem
@mod.Constraint()
def OPEX_calc(mod):
    return mod.OPEX == \
        sum(mod.POD_b[p].cost_electricity_v for p in mod.POD_s) -\
        sum(mod.POD_b[f].revenue_electricity_v for f in mod.POD_s) +\
        sum(mod.PDR_b[p].cost_total_v for p in mod.PDR_s) +\
        sum(mod.GENSET_b[g].cost_operationMaintenance_v for g in mod.GENSET_s) + \
        sum(mod.COGEN_b[c].cost_operationMaintenance_v for c in mod.COGEN_s) + \
        sum(mod.BOILER_b[d].cost_operationMaintenance_v for d in mod.BOILER_s) +\
        sum(mod.BESS_b[e].cost_operationMaintenance_v for e in mod.BESS_s) +\
        sum(mod.BESS_b[e].cost_minRevenuesCycle_v for e in mod.BESS_s) +\
        sum(mod.GENSET_b[g].cost_startUp_total_v for g in mod.GENSET_s) + \
        sum(mod.GENSET_b[g].cost_shutDown_total_v for g in mod.GENSET_s)
        

@mod.Constraint()
def Penalty_withdrawn(mod): #reduce withdrawn of the micro-grid
    return mod.penalty_withdrawn_v == sum(mod.POD_b[p].penalty_withdrawn_v for p in mod.POD_s) 
        
@mod.Constraint()
def Penalty_slack_calc(mod): #calculate penalty for non respecting setpoints
    return mod.penalty_slack_v == sum(mod.BESS_b[b].penalty_slack_v for b in mod.BESS_s) \
                                + sum(mod.POD_b[p].penalty_slack_v for p in mod.POD_s)
 
@mod.Constraint()
def Imbalance_penalty(mod): #avoid the system to imbalance the grid
    return mod.penalty_imbalance_v == sum(mod.POD_b[p].penalty_imbalance_v for p in mod.POD_s)

# # Objective Function of the problem
@mod.Objective()
def obj(mod):
    return mod.OPEX + mod.penalty_withdrawn_v + mod.penalty_slack_v + mod.penalty_imbalance_v #+ mod.bess_cycleRevenues_penalty_v






import pyomo

import pprint 
import os
import yaml
import pyomo.environ as pyo
from pyomo.util.infeasible import log_infeasible_constraints

import src.Model as ModelEMS

solver_name = 'gurobi' # requires Gurobi installation
time_limit = 1800 #s

# Insert the folder of the proposed test from the TEST_folder in "TEST_SELECTION"   
TEST_FOLDER = 'examples'
TEST_SELECTION  = '0_rescheduling'
TEST_NAME="input.txt"
FILE_PATH = './'+TEST_FOLDER+'/'+TEST_SELECTION

logic_loadYaml=True # True: load data from yaml files; False: load data from .txt files
if logic_loadYaml:
    data = {}
    for filename in os.listdir(path=FILE_PATH):
        yamlfile = FILE_PATH+"/"+filename
        if os.path.isfile(yamlfile) and yamlfile.endswith('.yaml'):
            with open(yamlfile,'r') as file:
                more_data = yaml.unsafe_load(file)
        
                for i in more_data.keys():
                    data[i]=more_data[i]
    
    data_final = {}
    data_final[None] = data
    #scrittura dizionario 
    with open(FILE_PATH+'/'+TEST_NAME, "w") as log_file:
            pprint.pprint(data_final, log_file, indent=4)
else:
    import ast
    content_file = open(FILE_PATH+'/'+TEST_NAME).read()
    data_final = ast.literal_eval(content_file)

instance = ModelEMS.mod.create_instance(data_final)

opt = pyomo.opt.SolverFactory(solver_name)
      
if solver_name=='gurobi':
    results = opt.solve(instance,symbolic_solver_labels=True,tee=True)

print("\nOPEX ORIGINAL")
print(pyo.value(instance.OPEX))
    
#scripting section

# for example, save solution for later use
if results['Solver'][0]['Termination condition'] in ["infeasible", "infeasibleOrUnbounded"]:
    import logging
    import sys
    logger = logging.getLogger(__name__)
    logger.level = logging.INFO
    
    file_handler = logging.FileHandler('infeasibility.log')
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.removeHandler(sys.stdout)
    
    log_infeasible_constraints(instance,log_expression=True, log_variables=True, logger=logger)
else:
    import cloudpickle as pickle 
    with open(FILE_PATH+'/solution.pkl', mode='wb') as file:
        pickle.dump(instance, file) 
        
    # Example of printing some results
    
    print("\nPENALTY WITHDRAWN")
    print(pyo.value(instance.penalty_withdrawn_v))
    
    print("\nPENALTY SLACK")
    print(pyo.value(instance.penalty_slack_v))
    
    print("\nPENALTY IMBALANCE")
    print(pyo.value(instance.penalty_imbalance_v))
    
    print("\nObjectiveFunction")
    print(pyo.value(instance.obj)) 

    

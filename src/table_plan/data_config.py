#EXAMPLE CONFIG

DELEGATE_CONFIG = {"path" : "src/table_plan/data/delegates.csv",
                      "col_map" :
                      {
                          "School Account (Conference Register)" : "organisation",
                          "first_name" : "First name",
                          "last_name" : "Surname",
                          "Job Title" : "Job Title",
                          "whole tables booked" : "whole tables booked"
                        },
                          "type" : "delegate"
                  }
                
EXHIBITOR_CONFIG = {"path" : "src/table_plan/data/exhibitors.csv",
                      "col_map" :
                      {
                          "company" : "organisation",
                          "first_name" : "First name",
                          "surname" : "Surname",
                          "Status Reason" : "Job Title",
                          "whole tables booked" : "whole tables booked"
                      },
                          "type" : "exhibitor"
                  }

INTERACTIONS_CONFIG = {"path" : "src/table_plan/data/interactions.csv",
                      "col_map" :
                      {
                          "Company" : "Company",
                          "school name" : "School"
                          }
                          }
    
DF_CONFIGS = {
    "DATA" : [DELEGATE_CONFIG, EXHIBITOR_CONFIG], 
    "INTERACTIONS" : INTERACTIONS_CONFIG
    }

from dataclasses import dataclass
from typing import Optional


@dataclass
class ModelInput:
    delegates: list[int]
    exhibitors: list[int]

    delegate_school: dict[int, int]
    exhibitor_company: dict[int, int]

    schools: set[int]
    companies: set[int]

    interactions: Optional[dict[tuple[int, int], int]] = None
    exclusive_schools : Optional[dict[int, int]] = None
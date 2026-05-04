#EXAMPLE CONFIG

DELEGATE_CONFIG = {"path" : "data\\delegates.csv",
                      "col_map" :
                      {
                          "School (Conference Register) (OptEd - Conference Register)" : "organisation",
                          "First Name" : "First name",
                          "Surname" : "Surname",
                          "Job Title" : "Job Title",
                          "whole tables booked" : "whole tables booked"
                        },
                          "type" : "delegate"
                  }
                
EXHIBITOR_CONFIG = {"path" : "data\\exhibitors.csv",
                      "col_map" :
                      {
                          "Account" : "organisation",
                          "Full name" : "First name",
                          "(Do Not Modify) SPEX attendees" : "Surname",
                          "Status Reason" : "Job Title",
                          "whole tables booked" : "whole tables booked"
                      },
                          "type" : "exhibitor"
                  }

INTERACTIONS_CONFIG = {"path" : "data\\interactions.csv",
                      "col_map" :
                      {
                          "Account (Exhibitor) (SPEX attendees)" : "Company",
                          "Account (Delegate) (OptEd - Conference Delegate)" : "School"
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
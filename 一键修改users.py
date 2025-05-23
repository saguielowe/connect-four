# -*- coding: utf-8 -*-
"""
Created on Sat Apr 12 17:08:20 2025

@author: 23329
"""
import json
all_user_data = {
    "default_account": "None",
    
}

with open("userdata/users.json", "w", encoding="utf-8") as f:
    json.dump(all_user_data, f, indent=2, ensure_ascii=False)
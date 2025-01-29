from ..components.db import User
from ..components.instance import local_data_list

def get_user_data():
    local_data_list.clear()
    users = User.query.all()
    for user in users:
        user_data = {
            'username': user.data['username'],
            'platform': user.data['platform'],
            'voteDelay': user.data['voteDelay'],
            'voteWeight': user.data['voteWeight'],
            'timestamp': user.data['timestamp']
        }   
        local_data_list.append(user_data)
    
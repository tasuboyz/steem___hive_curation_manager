def update_efficiency_average(author, current_efficiency, author_efficiency_dict):
    """Aggiorna l'efficienza media di un autore."""
    if author not in author_efficiency_dict:
        author_efficiency_dict[author] = {
            'total': current_efficiency,
            'count': 1,
            'average': current_efficiency
        }
    else:
        author_data = author_efficiency_dict[author]
        author_data['total'] += current_efficiency
        author_data['count'] += 1
        author_data['average'] = author_data['total'] / author_data['count']
    
    return author_efficiency_dict[author]['average']

def update_payout_average(author, current_payout, author_payout_dict):
    """Updates the average payout for an author."""
    if author not in author_payout_dict:
        author_payout_dict[author] = {
            'total': current_payout,
            'count': 1,
            'average': current_payout
        }
    else:
        payout_data = author_payout_dict[author]
        payout_data['total'] += current_payout
        payout_data['count'] += 1
        payout_data['average'] = payout_data['total'] / payout_data['count']
    
    return author_payout_dict[author]['average']
def select_next_node(current_node, destination_node, unvisited_nodes, distance_matrix):
    if not unvisited_nodes:
        return destination_node  # If all nodes are visited, return to the destination node
    
    def score(node):
        remaining = len(unvisited_nodes)
        avg_distance = sum(distance_matrix[current_node][n] for n in unvisited_nodes) / remaining
        exploration_bonus = (1 / (remaining**0.5)) * (1 / (avg_distance + 1))
        centrality_score = sum(distance_matrix[node][other] for other in unvisited_nodes) / (remaining**0.75)
        return 0.6 * distance_matrix[current_node][node] - (exploration_bonus * centrality_score) - (0.2 * distance_matrix[node][destination_node])
    
    next_node = min(unvisited_nodes, key=score)
    return next_node

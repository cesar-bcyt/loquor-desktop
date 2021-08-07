class Tree(object):
    def __init__(self, data1=None, data2=None, data3=None, parent=None):
        self.left = None
        self.right = None
        self.data1 = data1
        self.data2 = data2
        self.data3 = data3
        self.data = [data1, data2, data3]
        self.parent = parent

    def data_len(self):
        return [True for x in self.data if x is not None].count(True)

    def is_leaf(self):
        return self.left is None and self.right is None

    def __repr__(self):
        return str(self.data1) + ' | ' + str(self.data2) + ' | ' + str(self.data3)

root =                   Tree(['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L'], ['M', 'N', 'Ñ', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'X', 'Y', 'Z'])
root.left =              Tree(['A', 'B', 'C', 'D', 'E', 'F'], ['G', 'H', 'I', 'J', 'K', 'L'], parent=root)
root.right =             Tree(['M', 'N', 'Ñ', 'O', 'P', 'Q', 'R'], ['S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'], parent=root)

root.left.left =         Tree(['A', 'B', 'C'], ['D', 'E', 'F'], parent=root.left)
root.left.right =        Tree(['G', 'H', 'I'], ['J', 'K', 'L'], parent=root.left)
root.right.left =        Tree(['M', 'N', 'Ñ', 'O'], ['P', 'Q', 'R'], parent=root.right)
root.right.right =       Tree(['S', 'T', 'U'], ['V', 'W', 'X', 'Y', 'Z'], parent=root.right)

root.left.left.left =    Tree('A', 'B', 'C', parent=root.left.left)
root.left.left.right =   Tree('D', 'E', 'F', parent=root.left.left)
root.left.right.left =   Tree('G', 'H', 'I', parent=root.left.right)
root.left.right.right =  Tree('J', 'K', 'L', parent=root.left.right)

root.right.left.right = Tree('P', 'Q', 'R', parent=root.right.left)

root.right.right.left = Tree('S', 'T', 'U', parent=root.right.left)

root.right.left.left =       Tree(['M', 'N'], ['Ñ', 'O'], parent=root.right.left)
root.right.left.left.left =  Tree('M', 'N', parent=root.right.left.left)
root.right.left.left.right = Tree('Ñ', 'O', parent=root.right.left.left)

root.right.right.right =       Tree(['V', 'W'], ['X', 'Y', 'Z'], parent=root.right.right)
root.right.right.right.left =  Tree('V', 'W', parent=root.right.right.right)
root.right.right.right.right = Tree('X', 'Y', 'Z', parent=root.right.right.right)

def get_data(path):
    current_tree = root
    for part in path.split('/'):
        if part == 'left':
            current_tree = current_tree.left
        elif part == 'right':
            current_tree = current_tree.right
        elif part == 'parent':
            current_tree = current_tree.parent
    if current_tree is not None:
        return [current_tree.data, current_tree]
    return (None, None)

# This file is required to make Python treat directories as packages

def check_directories():
    """
    Utility function to check if necessary directories exist
    """
    import os
    
    directories = ['data', 'cogs']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        
    # Create __init__.py files in subdirectories if they don't exist
    for directory in ['cogs', 'utils']:
        init_file = os.path.join(directory, '__init__.py')
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write('# This file is required to make Python treat directories as packages')

list_of_args = ['one', 'two', 'three']

def printer(*args):
    for arg in args:
        print(arg)

printer(list_of_args)

printer(*list_of_args)

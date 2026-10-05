class typeutils:
    
    def get_keys(var):
        var = var.keys()
        var = str(var).removeprefix("dict_keys([").removesuffix("])")
        var = var.replace("\"'[]","")
        var = var.replace("'","")
        var = var.replace(" ","").split(",")
        print(var)
        return var
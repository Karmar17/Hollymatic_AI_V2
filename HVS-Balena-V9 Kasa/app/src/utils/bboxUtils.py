class bbox_utils:
    def bbox_lenght(bbox):
        x1,y1,x2,y2 = bbox
        base = abs(abs(x1 - x1) + abs(x2 - x1))
        alture = abs(abs(y1 - y1) + abs(y2-y1))

        if base > alture:
            lenght = base
            width = alture
        else:
            lenght = alture
            width = base

        bbox_aspect_ratio = width/lenght
        print(bbox_aspect_ratio)
        return bbox_aspect_ratio
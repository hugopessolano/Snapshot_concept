from urllib.parse import urlparse, parse_qs
from pydantic import BaseModel
from copy import deepcopy
import numpy as np
import json

#from pydantic_objects import Product

def extract_pages(link_string:str) -> list:
    #Recieves the string formatted acordingly to the header.link attribute from the get requests
    #and Returns a dataframe with the links for all the pages comprehended in that range
    extracted_links:list = [splitted[0] for splitted in [_.split(';') for _ in link_string.split(',')]]
    url_limits:list = [extracted_links[0].split('=')[0].strip('<') + "="] + [int(_.split('=')[1].strip('>')) for _ in extracted_links]
    urls = [f'{url_limits[0]}{i}' for i in range(url_limits[1],url_limits[2]+1)]
    
    return urls

def obtain_parameters(url:str) -> dict:
    #Recieves a url as string, and extracts it's query parameters 
    parsed_url = urlparse(url)
    params = parse_qs(parsed_url.query)

    return params

def format_attributes(obj:BaseModel, method:str) -> BaseModel|list|str:
    # Removes the unnecessary attributes from an object 
    if isinstance(obj, BaseModel):
        if '_exclusion_list' in list(obj.__private_attributes__.keys()):
            if method in list(obj._exclusion_list.keys()):
                [delattr(obj, attribute) for attribute in obj._exclusion_list[method]]
            else:
                raise ValueError(f'Value {method} is not a valid method for the selected object {obj}')
    elif isinstance(obj, list):
        return obj
    else:
        raise TypeError('Object must be an instance of Pydantic BaseModel')
    
    return obj

def jsonify(obj, method='FULL'):
    # Recursive function to format the provided object into JSON
    # based on the method provided (PUT, POST, FULL)
    new_obj = dict()

    if isinstance(obj, list):
        for i in range(len(obj)):
            obj[i] = jsonify(obj[i], method)
        else:
            new_obj = obj

    if isinstance(obj, BaseModel):
        obj = format_attributes(obj, method)
        for k,v in obj.__dict__.items():
            if v is not None:
                new_obj[k] = v if not isinstance(v,BaseModel) and not isinstance(v,list) else jsonify(v, method)
    else:
        return obj
    
    return new_obj

def products_are_equal(product_1, product_2) -> bool:
    #Converts the products to json, to compare them on their appropriate format (PUT, as it's more complete)
    return deepcopy(product_1).to_json('PUT') == deepcopy(product_2).to_json('PUT')

def exclude_missing_variants(obj_read:BaseModel, obj_fetched:BaseModel) -> list[BaseModel]:
    # Compares the object read from the json, and the one fetched from the API
    # Returns a list of the objects for the missing variants
    read_variants = obj_read.variants_list
    fetched_variants = set(obj_fetched.variants_list)
    
    variants_to_exclude = [variant for variant in read_variants if variant not in fetched_variants]
    excluded_variant_objects = [obj_read.variants_dict[f'{variant}'] for variant in variants_to_exclude]

    if len(variants_to_exclude) > 0:
        obj_read.remove_variants(variants_to_exclude)

    return excluded_variant_objects

def clusterize(object_list:list, cluster_limit:int) -> list:
    #Divide the provided list in evenly distributed clusters according to the provided cluster_limit
    if not object_list:
        return []
    
    if cluster_limit > len(object_list):
        cluster_limit = len(object_list)
    return [list(array) for array in (np.array_split(object_list, int(np.ceil(len(object_list) / cluster_limit))))]

def save_json_data(filename:str, json_data:dict):
    with open(filename, 'w') as file:
        json.dump(json_data, file) 

if __name__ == '__main__':
    #link_string = '<https://api.tiendanube.com/v1/3734860/products?page=2>; rel="next", <https://api.tiendanube.com/v1/3734860/products?page=10000>; rel="last"'
    #urls = extract_pages(link_string)
    url = 'https://api.tiendanube.com/v1/3734860/products'
    params = obtain_parameters(url)
    
 
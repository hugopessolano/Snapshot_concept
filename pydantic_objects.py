from pydantic import BaseModel, conint, PrivateAttr
from typing import Optional, List, Union, Dict
import json
from auxiliary_functions import jsonify

class LanguageString(BaseModel):
    es: Optional[str] = None
    en: Optional[str] = None
    pt: Optional[str] = None
    
class Attribute(BaseModel):
    es: Optional[str] = None
    en: Optional[str] = None
    pt: Optional[str] = None

class InventoryLevel(BaseModel):
    id: conint(gt=0)
    variant_id: conint(gt=0)
    location_id: str
    stock: Optional[conint(ge=0)] = None

class VariantValue(BaseModel):
    es: str

class Variant(BaseModel):
    id: conint(gt=0)
    image_id: Optional[conint(gt=0)] = None
    product_id: conint(gt=0)
    position: conint(ge=0)
    price: Optional[str] = None
    compare_at_price: Optional[str] = None
    promotional_price: Optional[str] = None
    stock_management: Optional[bool] = True
    stock: Optional[conint(ge=0)] = None
    weight: Optional[str] = "0"
    width: Optional[str] = "0"
    height: Optional[str] = "0"
    depth: Optional[str] = "0"
    sku: Optional[str] = None
    values: Optional[List[VariantValue]] = None
    barcode: Optional[str] = None
    mpn: Optional[str] = None
    age_group: Optional[str] = None
    gender: Optional[str] = None
    created_at: str
    updated_at: str
    cost: Optional[str] = None
    inventory_levels: Optional[List[InventoryLevel]] = None
    _exclusion_list: dict = PrivateAttr(default_factory=lambda: {
        'FULL':  ['_exclusion_list'],
        'PUT': ['created_at', 'updated_at', '_exclusion_list'],
        'POST': ['id', 'created_at', 'updated_at', 'image_id', 'inventory_levels', 'position', '_exclusion_list']
    })


    def to_json(self, method='FULL') -> dict:
        obj = self.model_copy()
        json_object = jsonify(obj, method)
        return json_object
                            

class Image(BaseModel):
    id: conint(gt=0)
    product_id: conint(gt=0)
    src: str
    position: conint(ge=0)
    alt: Optional[Union[List[Optional[str]], Dict[str, str]]] = None
    height: conint(gt=0)
    width: conint(gt=0)
    thumbnails_generated: conint(ge=0)
    created_at: str
    updated_at: str
    _exclusion_list: dict = PrivateAttr(default_factory=lambda: {
        'FULL':  ['_exclusion_list'],
        'PUT': ['alt', 'height', 'width', 'created_at', 'updated_at', 'thumbnails_generated','_exclusion_list'],
        'POST': ['id', 'alt', 'height', 'width','product_id', 'created_at', 'updated_at', 'thumbnails_generated','_exclusion_list']
    })
    
    

class Category(BaseModel):
    id: conint(gt=0)
    name: LanguageString
    description: Optional[LanguageString] = None
    handle: Optional[LanguageString] = None
    parent: Optional[int] = None
    subcategories: List[int] = []
    seo_title: Optional[LanguageString] = None
    seo_description: Optional[LanguageString] = None
    google_shopping_category: Optional[str] = None
    created_at: str
    updated_at: str
    _exclusion_list: dict = PrivateAttr(default_factory=lambda: {
        'FULL':  ['_exclusion_list'],
        'PUT': [ 'name', 'description', 'handle', 'parent', 'subcategories', 'seo_title', 
                 'seo_description', 'google_shopping_category', 'created_at', 'updated_at', '_exclusion_list'],
        'POST': [ 'name', 'description', 'handle', 'parent', 'subcategories', 'seo_title', 
                 'seo_description', 'google_shopping_category', 'created_at', 'updated_at', '_exclusion_list']
    })

class Product(BaseModel):
    id: conint(gt=0)
    name: Optional[LanguageString] = None
    description: Optional[LanguageString] = None
    handle: Optional[LanguageString] = None
    attributes: Optional[List[Attribute]] = None
    published: Optional[bool] = False
    free_shipping: Optional[bool] = False
    requires_shipping: Optional[bool] = True
    canonical_url: Optional[str] = None
    video_url: Optional[str] = None
    seo_title: Optional[LanguageString] = None
    seo_description: Optional[LanguageString] = None
    brand: Optional[str] = None
    created_at: str
    updated_at: str
    variants: List[Variant]
    tags: Optional[str] = None
    images: Optional[List[Image]] = None
    categories: Optional[List[Category]] = None
    _exclusion_list: dict = PrivateAttr(default_factory=lambda: {
        'FULL':  ['_exclusion_list'],
        'PUT': ['created_at','canonical_url', 'updated_at',  'images', '_exclusion_list'],
        'POST': ['id','canonical_url', 'created_at', 'updated_at', 'images', '_exclusion_list']
    })

    @property
    def variants_list(self) -> list:
        return [variant.id for variant in self.variants]
    
    @property
    def categories_list(self) -> list:
        return [category.id for category in self.categories]
    
    @property
    def variants_dict(self) -> dict: 
        return {f'{variant.id}': variant for variant in self.variants}

    def tweak(self, json_object):
        json_object['categories'] = [item['id'] for item in json_object['categories']]
        return json_object
        

    def to_json(self, method='FULL') -> dict:
        obj = self.model_copy()
        json_object = jsonify(obj, method)
        json_object = self.tweak(json_object)
        return json_object
    
    def remove_variants(self, variants_to_remove:list[str]) -> None:
        for variant in variants_to_remove:
            variant = self.variants_dict[f'{variant}']
            self.variants.remove(variant)
    
    def __repr__(self):
        return f'Product Object: id={self.id}, name={self.name.es}, variants={self.variants_list}, categories={self.categories_list}'


if __name__ == '__main__':
    json_file = '3734860 - Snapshot product 184139334.json'
    
    with open(json_file, 'r') as file:
        json_data = json.load(file)
    
    product = Product(**json_data)
    product_json = product.to_json(method='PUT')
    
    savefile = 'test.json'
    with open(savefile, 'w') as file:
        json.dump(product_json, file) 
    print(product)
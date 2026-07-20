# -*- coding: utf-8 -*-
"""
Created on Fri Jul 17 12:33:24 2026

Given trader prices determine if it is worth it to craft and resell rare materials
using artisans

@author: Jameson Rigg
"""

import datetime as dt
from pathlib import Path

import pandas as pd

DATA_DIRECTORY = Path(__file__).parents[1] / 'csv'

DEFAULT_PRICES_PATH = DATA_DIRECTORY / 'prices.csv'
DEFAULT_RECIPES_PATH = DATA_DIRECTORY / 'recipes.csv'

class Location:
    def __init__(self, location_name: str):
        self.name = location_name

class Crafter:
    def __init__(self, crafter_name: str):
        self.name = crafter_name


class Material:
    def __init__(self, material_name: str):
        self.name = material_name
    
    def __repr__(self):
        return self.name


class ArtisanRecipe:
    def __init__(
            self,
            required_materials: dict[Material:int],
            transaction_cost: int, 
            return_material: Material,
            ):
        self.required_materials = required_materials
        self.transaction_cost = transaction_cost
        self.return_material = return_material

    def __repr__(self):
        return f'{self.return_material}: {self.required_materials}'


class Artisan:
    def __init__(
            self,
            name: str,
            recipes: list[ArtisanRecipe],
            location: Location,
            ):
        self.name = name
        self.recipes = recipes
        self.location = location


def create_recipes(recipe_df: pd.DataFrame) -> list[ArtisanRecipe]:
    # Assume no crafter has multiple recipes for the same item
    crafters_materials = recipe_df.groupby(['Recipe Crafter', 'Return Material'])
    
    recipes = {}
    for crafter, return_material in crafters_materials.groups:
        df = crafters_materials.get_group((crafter, return_material))
        materials = df[['Required Material', 'Required Amount']].set_index('Required Material')
        
        required_materials = {}
        for material in materials.index:
            required_materials.update({Material(material) : materials.at[material, 'Required Amount']})
        
        transaction_cost = df['Recipe Cost'].max()
        
        recipe = ArtisanRecipe(required_materials, transaction_cost, return_material=return_material,)
        recipes.update({(crafter, return_material) : recipe})
    return recipes
        

def determine_material_cost(
        material: Material, 
        material_quantity: int, 
        prices: pd.DataFrame,
        *,
        material_cost_column_name='Trader Sell Price'
        ):
    try:
        material_cost = prices.at[material.name, material_cost_column_name] * material_quantity
    except:
        raise Exception(f'Could not find price for {material.name}')
    return material_cost
    


def determine_recipe_cost(recipe: ArtisanRecipe, prices: pd.DataFrame):
    material_costs = {}
    for material_name, quantity in recipe.required_materials.items():
        cost = determine_material_cost(material_name, quantity, prices)
        material_costs.update({material_name : cost})
    recipe_cost = sum(material_costs.values()) + recipe.transaction_cost
    return recipe_cost


def determine_recipe_sell_price(
        recipe: ArtisanRecipe, 
        prices: pd.DataFrame,
        *,
        material_sell_value_column_name='Trader Buy Price'):
    return prices.at[recipe.return_material, material_sell_value_column_name]

def determine_recipe_return(
        recipe: ArtisanRecipe, 
        prices: pd.DataFrame,
        ):
    trader_purchase_price = determine_recipe_sell_price(recipe, prices)
    recipe_cost = determine_recipe_cost(recipe, prices)
    return_amount = trader_purchase_price - recipe_cost
    return return_amount


def create_recipe_return_df(recipes_df: pd.DataFrame, prices: pd.DataFrame):
    recipes = create_recipes(recipes_df)
    
    recipes_costs = []
    for key, recipe in recipes.items():
        # TODO need a better way to get this
        crafter = key[0]
        material = recipe.return_material
        cost = determine_recipe_cost(recipe, prices)
        sell_price = determine_recipe_sell_price(recipe, prices)
        return_amount = determine_recipe_return(recipe, prices)
        
        return_ser = pd.Series(
            {
                'Crafter' :  crafter,
                'Return Material' : material,
                'Sell Price' : sell_price,
                'Cost' : cost,
                'Return Amount': return_amount,
                
            })
            
        recipes_costs.append(return_ser)
    
    results = pd.DataFrame(recipes_costs)
    return results


def main(prices_path: Path=DEFAULT_PRICES_PATH, recipes_path: Path=DEFAULT_RECIPES_PATH) -> pd.DataFrame:
    prices = pd.read_csv(prices_path).set_index('Material Name')
    recipes_df = pd.read_csv(recipes_path)
    
    results = create_recipe_return_df(recipes_df, prices)
    return results


if __name__ == '__main__':
    summary_results = main()
    profit = summary_results[summary_results['Return Amount'] > 0]

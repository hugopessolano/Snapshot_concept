from auxiliary_functions import extract_pages, obtain_parameters, exclude_missing_variants, products_are_equal, clusterize, save_json_data
import asyncio
import json
import httpx
from datetime import datetime
from rich.console import Console
from rich.progress import track
import pandas as pd
import httpx
import asyncio
import numpy as np
import itertools
from pydantic_objects import Product
import os

CONSOLE = Console()
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

class RequestManager:
    """
    Request handler. Executs the requests and Stores the responses.
    """
    MAX_CLUSTER_SIZE:int = 40
    URL:str = 'https://api.tiendanube.com/v1'
    
    def __init__(self, store_id, access_token) -> None:
        self._store_id = store_id
        self._access_token:str = access_token
        self._url = f'{self.URL}/{store_id}'
        self._headers:dict = self.build_headers()
    
    @property
    def url(self):
        return self._url
    
    @property
    def headers(self):
        return self._headers

    @property
    def access_token(self):
        return self._access_token
    
    @property
    def store_id(self):
        return self._store_id


    def build_headers(self) -> dict:
        headers = {
                'Authentication': self.access_token,
                'Content-Type': 'application/json',
                'User-Agent': 'tech-support@tiendanube.com'
            }
        return headers

    async def build_get_request_task(self, client:httpx.AsyncClient, url_overlap=None) -> list:
        """
        Crea y retorna la taréa de ejecución para cada request
        Cada taréa se ejecutará posteriormente en su cluster correspondiente
        """
        url = url_overlap if url_overlap else f'{self.url}/products'
        params = obtain_parameters(url)
        page = params['page'][0] if len(params) > 0 else 1
        response = client.get(url, headers=self.headers, timeout=None)

        return [response, page]

    def build_product_request(self, product_json:dict) -> list:
        # Builds the list to be used as an argument for the product request execution.
        url = f'https://api.tiendanube.com/v1/{self.store_id}/products'
        if 'id' in product_json:                # It's a put request
            url += f'/{product_json.pop('id')}' # So we add the id to the endpoint url 
        
        payload = product_json

        return [url, payload]

    def build_variants_put_request(self, product_id:str, variants_json:list) -> list:
        # Builds the list to be used as an argument for the Variant PUT request execution.
        url = f'https://api.tiendanube.com/v1/{self.store_id}/products/{product_id}/variants'
        payload = variants_json

        return [url, payload]
    
    def build_variant_post_request(self, variant_json:dict) -> list:
        # Builds the list to be used as an argument for the Variant POST request execution.
        url = f'https://api.tiendanube.com/v1/{self.store_id}/products/{variant_json.pop("product_id")}/variants'
        payload = variant_json
        
        return [url, payload]

    async def execute_request(self, client:httpx.AsyncClient, request_content:list, method:str) -> httpx.Response:
        # Executes the request based on the method string provided
        url, payload = request_content[0],request_content[1]
        
        match method:
            case 'PUT':
                response = client.put(url, headers=self.headers, json=payload, timeout=None)
            case 'POST':
                response = client.post(url, headers=self.headers, json=payload, timeout=None)
            case _:
                CONSOLE.print([f'[bold red]No method available matching: {method}[/bold red]'])
                raise httpx.RequestError(f'No method available matching: {method}')
        
        return response

    async def gather_products(self) -> list:
        # Fetches evey product in the store
        # And returns it in json and dataframe formats
        results_jsons_list = []
        results_dfs_list = []

        async with httpx.AsyncClient() as client:
            # Fetches the first bundle of products
            first_request = await asyncio.create_task(self.build_get_request_task(client))
            response:httpx.Response = await asyncio.gather(first_request[0])
            response = response[0]

            if response.is_success: # If the first bundle is fetched properly
                results_dfs_list.append(pd.DataFrame(response.json()))
                results_jsons_list.append(response.json())
                pages = extract_pages(response.headers['link']) # Extract and build the links for the subsequent requests
            else:
                CONSOLE.print(f'[bold red]Your request returned an error {response.text}[/bold red]')
                raise httpx.HTTPStatusError(f'Your request returned an error {response.status_code}')
            
            # Build the rest of the GET requests to fetch, based on the extracted pages. 
            tasks = [asyncio.create_task(self.build_get_request_task(client, url)) for url in pages]
            #task_clusters = [list(array) for array in (np.array_split(tasks,int(np.ceil(len(tasks)/self.MAX_CLUSTER_SIZE))) )]
            task_clusters = clusterize(tasks, self.MAX_CLUSTER_SIZE)

            CONSOLE.print(f"[bold green]{len(tasks)}[/bold green][bold blue] tasks have been divided into[/bold blue][bold green] {len(task_clusters)}[/bold green] [bold blue]clusters[/bold blue]")
            for cluster in track(task_clusters, description='Fetching Clusters... '):
                cluster_plan = await asyncio.gather(*cluster)
                rq_tasks = [task[0] for task in cluster_plan]
                # rq_pages = [task[1] for task in cluster_plan]
                
                responses = await asyncio.gather(*rq_tasks)

                for response in responses:
                    if response.is_success:
                        results_dfs_list.append(pd.DataFrame(response.json()))
                        results_jsons_list.append(response.json())
                    else:
                        raise httpx.HTTPStatusError(f'Your request returned an error {response.status_code}')
            
        results_json = list(itertools.chain(*results_jsons_list))
        results_df = pd.concat(results_dfs_list)
        
        return [results_df, results_json]
    
    async def build_tasks(self, row:pd.Series) -> pd.Series:
        # Row method to build the method tasks within the working dataframe
        row['product_request'] = self.build_product_request(row['product_json'])
        
        if row['variants_json']: #If it's not None
            # Extract the product ID and remove it from the JSON
            product_id = list(set([variant.pop('product_id') for variant in row['variants_json']]))[0] 
            row['variant_put_request'] = self.build_variants_put_request(product_id, row['variants_json']) #Then build the request

        # Variants Post can contain multiple items, so it's a list. Hence we evaluate length.
        if len(row['missing_variants_json']) > 0: 
            product_id = list(set([variant.pop('product_id') for variant in row['missing_variants_json']]))[0]
            row['variant_post_request'] = self.build_variants_put_request(product_id, row['missing_variants_json'] )
        
        return row
        
    async def prepare_execution(self, row:pd.Series, client:httpx.AsyncClient) -> pd.Series:
        # Row method which builds the async request execution tasks for further clustering and awaiting
        # And stores them in their respective columns
        product_request:list = row['product_request']
        variant_put_request:list = row['variant_put_request']
        variant_post_request:list = row['variant_post_request']

        row['product_response'] = asyncio.create_task(self.execute_request(client, request_content=product_request, method=row['action']))
        if variant_put_request:
            row['variant_put_response'] = asyncio.create_task(self.execute_request(client, request_content=variant_put_request, method='PUT'))
        if variant_post_request:
            row['variant_post_response'] = [asyncio.create_task(self.execute_request(client, request_content=[variant_post_request[0], payload], method='POST'))
                                            for payload in variant_post_request[1]]
        return row
        

    async def restore_products(self, df:pd.DataFrame) -> pd.DataFrame:
        # Executes the restore function based on the actions dataframe.
        df[['product_request', 'variant_put_request', 'variant_post_request',
            'product_response', 'variant_put_response', 'variant_post_response']] = '' # Add execution and diagnosis columns
        
        CONSOLE.print(f"[bold blue]Building tasks for each product[/bold blue]")
        request_content_tasks = [asyncio.create_task(self.build_tasks(row)) for _, row in df.iterrows()] # Populate the request columns
        contents_list = await asyncio.gather(*request_content_tasks)
       
        df = pd.DataFrame(contents_list) # Replace the main dataframe with the updated version

        CONSOLE.print(f"[bold blue]Preparing to execute requests[/bold blue]")
        async with httpx.AsyncClient() as client:
            tasks = [asyncio.create_task(self.prepare_execution(row, client)) for _,row in df.iterrows()] # Build the actual request tasks
            ready_task_rows = await asyncio.gather(*tasks)
            df = pd.DataFrame(ready_task_rows) # Replace the main dataframe with the updated version

            product_tasks = df['product_response'].to_list()
            variant_put_tasks = [_ for _ in df['variant_put_response'].to_list() if _ != '']
            variant_post_tasks = list()
            
            grouped_variant_posts = df['variant_post_response'].to_list()
            for task_group in grouped_variant_posts: # Extract the post tasks from comfy little lists
                for task in task_group:
                    variant_post_tasks.append(task)

            product_task_clusters = clusterize(product_tasks, self.MAX_CLUSTER_SIZE)
            variant_task_clusters = clusterize(variant_put_tasks+variant_post_tasks, self.MAX_CLUSTER_SIZE)

            CONSOLE.print(f"[bold green]{len(product_tasks)}[/bold green][bold blue] tasks have been divided into[/bold blue][bold green] {len(product_task_clusters)}[/bold green] [bold blue]clusters for the Product Actions[/bold blue]")
            CONSOLE.print(f"[bold green]{len(variant_put_tasks+variant_post_tasks)}[/bold green][bold blue] tasks have been divided into[/bold blue][bold green] {len(variant_task_clusters)}[/bold green] [bold blue]clusters for the Variant Actions[/bold blue]")

            processed_product_responses = dict()
            processed_variant_responses = dict()

            for cluster in track(product_task_clusters, description='Executing Product Clusters... '):
                cluster_plan = await asyncio.gather(*cluster)
                responses = await asyncio.gather(*cluster_plan)
                processed_product_responses.update(dict(zip(cluster,responses)))
            
            for cluster in track(variant_task_clusters, description='Executing Variant Clusters... '):
                cluster_plan = await asyncio.gather(*cluster)
                responses = await asyncio.gather(*cluster_plan)
                processed_variant_responses.update(dict(zip(cluster,responses)))

            CONSOLE.print(f"[bold green]FINISHED processing requests[/bold green]")
            CONSOLE.print(f"[bold blue]Preparing log dataframe[/bold blue]")
            #df['product_response'] = df['product_response'].map(processed_product_responses).fillna('non value')
            #Once everything is executed, store the responses by replacing the completed tasks
            df['product_response'] = df['product_response'].apply(lambda x: processed_product_responses.get(x, x))
            df['variant_put_response'] = df['variant_put_response'].apply(lambda x: processed_variant_responses.get(x, x))
            df['variant_post_response'] = df['variant_post_response'].apply(lambda lst: [processed_variant_responses.get(x, x) for x in lst])

        return df
        

class ExecutionManager:
    """
    Builds, stores and handles the information necessary to execute the requests.
    Uses RequestManager to run the requests, and logs the result. TODO: Create a LogManager class.
    """
    def __init__(self, store_id, access_token):
        self._store_id:str = store_id
        self._access_token:str = access_token
        self._request_manager:RequestManager = self.build_request_manager()
        self._fetched_products_json = dict()
        self._last_exported_json = None
        self._read_products_dataframe = pd.DataFrame()
        self._tasks_dataframe = pd.DataFrame()
        self._ignored_tasks = pd.DataFrame()
        
    
    @property
    def access_token(self):
        return self._access_token
    
    @property
    def store_id(self):
        return self._store_id
    
    @property 
    def fetched_products_json(self):
        return self._fetched_products_json

    @property
    def last_exported_json(self):
        return self._last_exported_json
    
    @property
    def read_products_dataframe(self):
        return self._read_products_dataframe
    
    @property
    def tasks_dataframe(self):
        return self._tasks_dataframe
    
    @property
    def ignored_tasks(self):
        return self._ignored_tasks

    @read_products_dataframe.setter
    def read_products_dataframe(self, new_dataframe:pd.DataFrame) -> None:
        self._read_products_dataframe = new_dataframe

    @tasks_dataframe.setter
    def tasks_dataframe(self, new_dataframe:pd.DataFrame) -> None:
        self._tasks_dataframe = new_dataframe

    @ignored_tasks.setter
    def ignored_tasks(self, new_dataframe:pd.DataFrame) -> None:
        self._ignored_tasks = new_dataframe

    def build_request_manager(self)-> RequestManager:
        return RequestManager(self.store_id, self.access_token)
    
    def build_fetched_products_json(self) -> None:
        # Gets every product from the designated store
        # And holds the json in memory
        CONSOLE.print(f"[bold blue]Attempting to fetch products[/bold blue]")
        try:
            self._fetched_products_json = asyncio.run(self._request_manager.gather_products())[1]
        except Exception as e:
            CONSOLE.print("[bold red]There was an error gathering the products. The process was aborted and no changes were made[/bold red]")
            CONSOLE.print(f"[bold yellow]{e}[/bold yellow]")

    def save_json(self) -> str:
        # Checks if a products_json is in memory and exports it to the script directory
        # Returns the full path to the file
        if self.fetched_products_json:
            CONSOLE.print(f"[bold blue]Exporting JSON to the execution folder[/bold blue]") # TODO: Añadir seleccion de ubicacion para el export 
            json_file_export = os.path.join(SCRIPT_DIR, f'{self.store_id} - Snapshot {datetime.now().strftime("%Y-%m-%d %H:%M")}.json')
            
            save_json_data(json_file_export, self.fetched_products_json)
            
            self._last_exported_json = json_file_export
            CONSOLE.print(f"[bold green]Successfully exported JSON: {json_file_export}[/bold green]")
            return json_file_export
        else:
            CONSOLE.print("[bold red]There's no json stored for export. Please load or generate a json first[/bold red]")

    def parse_json(self, json_obj:dict) -> list[Product|None]:
        # Converts the products on the provided JSON to the Product object
        # With it's respective validations
        products_list = []
        
        CONSOLE.print(f"[bold blue]Parsing products[/bold blue]")
        if len(json_obj) > 0:
            products_list = [Product(**product) for product in json_obj] # Unpacks and converts
        CONSOLE.print(f"[bold green]Successfully parsed {len(products_list)} products![/bold green]")
        return products_list

    def load_json_file(self, json_file:str) -> None:
        # Reads a json backup file, parses it into Product objects
        # And stores them as a dataframe in memory
        CONSOLE.print(f"[bold blue]Attempting to read json file {json_file}[/bold blue]")
        try:
            with open(json_file, 'r') as file:
                json_data = json.load(file)
        except Exception as e:
            CONSOLE.print(f"[bold red]Failed reading json file {json_file}, \nException message: {e}[/bold red]")
            raise BufferError(f'Error loading file: {json_file}')
        
        CONSOLE.print(f"[bold blue]Working on read products[/bold blue]")
        products_list = self.parse_json(json_data)

        self.read_products_dataframe = pd.DataFrame({'read_product_object':products_list})

    def is_ready_for_restore(self) -> bool:
        # Pre-restore validations
        try:
            return self.read_products_dataframe.size > 0
        except:
            return False

    def evaluate_action(self, row:pd.Series) -> pd.Series:
        # Row function which determines what will be done for the elements in the
        # dataframe
        read_product = row['read_product_object']
        fetched_product = row['fetched_product_object']
        action = 'IGNORE'

        if pd.isna(fetched_product): #Product doesn't exist currently, so it was deleted
            action = 'POST'
        elif not products_are_equal(read_product, fetched_product): # Changes were made to the product
            action = 'PUT'

        return pd.Series([read_product, fetched_product, action])

    def extract_product_and_variants_json(self, row:pd.Series) -> pd.Series:
        # Row function Which evaluates the correct JSON format for each object and conerts it accordingly
        # finally it returns the series object to be assigned in their respective json rows
        read_obj: Product = row['read_product_object']
        fetched_obj: Product = row['fetched_product_object']
        action:str = row['action']
        # extract variants which were deleted, and format them for POST
        missing_variants: list = exclude_missing_variants(read_obj, fetched_obj) if not pd.isna(fetched_obj) else list()
        missing_variants = [variant.to_json('POST') for variant in missing_variants]

        json_read_obj = read_obj.to_json(method=action) # Convert products to the necessary json format
        variants = json_read_obj.pop('variants') if action == 'PUT' else None # And extract the variants to update separately

        return pd.Series([json_read_obj, variants, missing_variants])

    def build_actions_dataframe(self) -> pd.DataFrame:
        # Compares the read products vs the fetched products dataframes, and evaluates which actions to take
        # Returns the dataframe with the actions included
        df_read = self.read_products_dataframe
        df_read['product_id'] = df_read['read_product_object'].apply(lambda x: x.id) # Extract the product ids
        
        CONSOLE.print(f"[bold blue]Building fetched products dataframe[/bold blue]")
        df_fetched = pd.DataFrame({'fetched_product_object':self.parse_json(self.fetched_products_json)}) # Build fetched objects df
        df_fetched['product_id'] = df_fetched['fetched_product_object'].apply(lambda x: x.id) # Extract the product ids for them

        df = pd.merge(df_read, df_fetched, on='product_id', how='left') # left join read vs fetched
        
        CONSOLE.print(f"[bold blue]Evaluating actions to take[/bold blue]")
        df[['read_product_object','fetched_product_object','action']] = df.apply(self.evaluate_action, axis=1) 
        self.ignored_tasks = df[df['action'] == 'IGNORE']
        
        df = df[df['action'] != 'IGNORE']
        if not df.empty:
            CONSOLE.print(f"[bold blue]Extracting pertinent data[/bold blue]")
            df[['product_json', 'variants_json', 'missing_variants_json']] = df.apply(self.extract_product_and_variants_json, axis=1) # split variant data for PUT operations
        return df

    def execute_snapshot_restore(self):
        if self.is_ready_for_restore():
            actions: pd.DataFrame = self.build_actions_dataframe()
            if not actions.empty:
                CONSOLE.print(f'[bold blue]Preparing to restore: [/bold blue] [bold green]{actions['product_id'].size}[/bold green] [bold blue]products[/bold blue]')
                results: pd.DataFrame = asyncio.run(self._request_manager.restore_products(actions))
                return results
            else:
                CONSOLE.print(f'[bold red]No actions to perform[/bold red]')
                return actions


if __name__ == "__main__":

    ##################################################################################
    ########## Following this line are the variables you should edit #################
    ##################################################################################

    STORE_ID = '3734860' 
    ACCESS_TOKEN = '1809de5c159e5919bfa663e64bff58b2ed80f4df'

    ##################################################################################
    execution_manager = ExecutionManager(STORE_ID, ACCESS_TOKEN)
    execution_manager.build_fetched_products_json()
    #execution_manager.save_json() #Back up the data before breaking stuff
    
    #execution_manager.load_json_file('3734860 - Snapshot 2024-08-24 15:32.json')
    json_file = os.path.join(SCRIPT_DIR, '3734860 - Snapshot 2024-09-17 19:36.json')
    execution_manager.load_json_file(json_file)
    
    results = execution_manager.execute_snapshot_restore()
    print('yey')
    



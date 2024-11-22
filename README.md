# Snapshot_concept
Concept for a scalable snapshot solution

# Installation
## Basic Requirements:
Make sure to have installed any version of Python 3.12 or above. This project should work properly with any version over 3.10, but .12 has some major optimizations to the runtime.
It will also be very convenient for you to have installed Vscode, and the python extension, but it's not really a requirement per se.

## Where do we begin?
First of all, move to a directory of your choosing, and clone the repository in it:
* `cd your/target/directory`
* `git clone git@github.com:hugopessolano/Snapshot_concept.git`
* `cd Snapshot_concept`

Once that's done we need to install the dependencies. I recommend doing so in a virtual environment to make sure the versions match with the required ones, and to keep them from interfering with your other python projects (Should you have any, which in my opinion, you absolutely **shoud**)

### SKIP THIS PART IF YOU DONT WANT A VIRTUAL ENVIRONMENT
Head over to your terminal, make sure you're on your target directory as stated previously, and type in the following commands:
1. Create the virtual environment:
`python3 -m venv your_environment_name`

2. Activate it
`source nombre_entorno/bin/activate`

If everything is ok you should see something like this, with your defined environment name in it:
![image](https://github.com/user-attachments/assets/d46a6ebd-12a2-4c06-ac7e-e3980ffe2e44)

##########################################################

Now that we have (or not) our virtual environment ready, we'll install the dependencies. It's as simple as running the following comand:
`pip3 install -r requirements.txt`

This will take a minute or two at most. Make sure to let me know if you find any difficulties and I'll make sure to help you out =)


# Running the project
## Step by step
If you installed vscode and the python extension, you should be able to open the `endpoint_poc.py` file, and see this play button on the top right corner of your editor:
![image](https://github.com/user-attachments/assets/b3d02145-e053-44bc-81d7-94bc0063a2d8)

If that's your case, all you need to do is click on that button, and it'll run the script for you.
If that's NOT your case, you can also run it by using the following command:
`python3 endpoint_poc.py`

This will start a local API with which you can interact. You should see a message like this one appear on your console:
<img width="538" alt="image" src="https://github.com/user-attachments/assets/92359d04-2d92-420f-9e44-965f35ae0dea">

## Usage
With our local API running, we'll be able to access it's endpoints.
If you access the provided address and specified port through your web browser, you should get something like this: <br>
![image](https://github.com/user-attachments/assets/8b9506b1-9dec-4ca4-89a7-a5815a2cf632)

Of course you can access it through postman, but i recommend the browser approach, as it's quicker and more practical. It'll be clearer in the next steps.

Having confirmed that our API is running locally, we can access the documentation by adding `/docs` at the end. We'll be able to test it here.
`http://127.0.0.1:8000/docs`
or
`http://localhost:8000/docs`

Either of those will take you to this page, in which you can check the active endpoints:
* Root ('/') - Which serves only as a health check, and is the greeting you saw when you first accessed the api
* Restore ('/restore') 
* Snapshot ('/snapshot')
![image](https://github.com/user-attachments/assets/5b1ffe3c-95c0-4e03-a55b-4beabd4a7be2)

To test each one out we can expand either of the endpoint docs by clicking on it, and enabling the "Try it out" option on the top right corner of it's container:
![image](https://github.com/user-attachments/assets/d70d14d4-38b3-470b-8858-00a3ddc332d6)

This will enable the argument fields. Here you will provide the designated arguments which will be sent to the endpoint in order to process the order.

## The Snapshot endpoint
This first example is from the **snapshot** endpoint, which takes in:
* store_id: The ID from the store that we want to generate a snapshot or backup for
* access_token: The bearer token from our user within the store.
  
Once you've completed the arguments, just click on the "Execute" button which should be fairly visible: <br>
![image](https://github.com/user-attachments/assets/b1c828f0-b5bf-4f95-89a1-a9813a8fcb02)

When you hit execute, a few cool things are going to happen.
On our "Server" side, our console will register what it's doing with a neat little progress bar: <br>
<img width="842" alt="image" src="https://github.com/user-attachments/assets/e7ea38c5-c191-4b0c-b80d-d026eec5343b">

It'll fetch all the store's products from our API (https://tiendanube.github.io/api-documentation/resources/product) and export them into a JSON. Currently it's stored on the root folder of our application, but it can be quickly changed to a different target.

_In the previously provided example we can see it took 7 seconds to fetch and convert +6000 products (How cool is that?)_

On our Client side, if we scroll down a bit, we'll be able to download the json file which was returned from the API:
_(Click on it to download)_
![image](https://github.com/user-attachments/assets/8c032839-a420-4967-924f-90497a3e9fe8)

## The Restore endpoint
Similarly to the previous one, this endpoint takes the **store_id** and **access_token** arguments, except this time we'll need to provide the snapshot JSON file consistent with the previously exported one:
![image](https://github.com/user-attachments/assets/f206c27d-98d8-45ca-b5f7-a4c564086dc5)

If the file we provide presents no differences from the current state of our store, no actions will be taken, and nothing will be changed. 
I'll delete a few products, variants, and modify some data in order to trigger modifications. Keep in mind that **only the products and/or variants detected as changed will be altered or re-created**

Once again, when we execute the magic will start happening on our server side:
<img width="770" alt="image" src="https://github.com/user-attachments/assets/18a518d8-03b5-43e4-ad43-21e48b9de92b">

* First it will render the products read from the provided/uploaded file
* Next it will fetch the products from our API reusing the same structure from the **snapshot** endpoint <br>
  _It is at this point where the integrity validations will be made using the pydantic models defined on a separate module_   
* Then it will compare the contents of both to check for differences
* Finally it will build the necessary requests and execute them to PUT or POST the products and variants that were altered

Once again, the uploaded file is stored on the "uploads" folder which is created upon execution, but this can be easily changed.

Feel free to branch and alter this as much as you like =) <br>
**_Long live the Python_**

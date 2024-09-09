# mokSa.ai_code


Steps to run:
1. Create a python conda environment 
  - conda create --name moksa python=3.10

2. install dependencies
   cd mokSa.ai_code
   pip install -r requirements.txt

3. run the fastapi uvicorn server
   cd src
   uvicorn main:app --reload --port 9009

   This will create a SqlLite3 db along and start running the Kakfa mock server 

I'm running a mock kakfa server to stream message
Uncomment kakfa code to integrate with real kakfa server 

I'm using websockets to stream data to the html table 
I'm using lru cache to cache history endpoints 


![image](https://github.com/user-attachments/assets/665eda7c-3648-4a99-bddd-51922421e728)




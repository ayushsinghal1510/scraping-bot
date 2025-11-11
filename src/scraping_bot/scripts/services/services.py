import time
import inspect
import functools

from logging import Logger

def method_log_timer(func) : 
    '''
    Decorator to log the execution time of a method.
    
    Args : 
        - func (callable): The method to be decorated.
        
    Returns : 
        - callable: The wrapped method with logging functionality.
    '''

    @functools.wraps(func)
    async def async_wrapper(self, *args , **kwargs) : 
        '''
        Asynchronous wrapper for the method to log execution time.
        
        Args : 
            - self: The instance of the class.
            - *args: Positional arguments for the method.
            - **kwargs: Keyword arguments for the method.
            
        Returns : 
            - result: The result of the method execution.
        '''

        logger : Logger | None = getattr(self , 'logger' , None)
        
        start_time = time.perf_counter()
        result = await func(self , *args , **kwargs)
        duration = time.perf_counter() - start_time
        
        if logger : logger.info(f'⏱️ Execution time for "{func.__name__}": "{duration:.4f}" seconds , response : "{result}"')
        else : print(f'Self.logger not found')

        return result

    @functools.wraps(func)
    def sync_wrapper(self, *args, **kwargs) : 
        '''
        Synchronous wrapper for the method to log execution time.
        
        Args :
            - self: The instance of the class.
            - *args: Positional arguments for the method.
            - **kwargs: Keyword arguments for the method.
            
        Returns : 
            - result: The result of the method execution.
        '''

        logger : Logger | None = getattr(self , 'logger' , None)

        start_time = time.perf_counter()
        result = func(self , *args , **kwargs)
        duration = time.perf_counter() - start_time

        if logger : logger.info(f'⏱️ Execution time for "{func.__name__}" : {duration:.4f} seconds , response : "{result}"')
        else : print(f'Self.logger not found')

        return result

    if inspect.iscoroutinefunction(func) : return async_wrapper
    else : return sync_wrapper
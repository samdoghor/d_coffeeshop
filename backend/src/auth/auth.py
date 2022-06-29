import json
from flask import request, _request_ctx_stack
from functools import wraps
from jose import jwt, ExpiredSignatureError, JWTError
from urllib.request import urlopen

#Extra Imports
import os
from dotenv import load_dotenv
from rsa import DecryptionError
load_dotenv()

AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN')
ALGORITHMS = os.getenv('ALGORITHMS')
API_AUDIENCE = os.getenv('API_AUDIENCE')

## AuthError Exception
'''
AuthError Exception
A standardized way to communicate auth failure modes
'''
class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


## Auth Header

'''
@TODO implement get_token_auth_header() method
    it should attempt to get the header from the request
        it should raise an AuthError if no header is present
    it should attempt to split bearer and the token
        it should raise an AuthError if the header is malformed
    return the token part of the header
'''
def get_token_auth_header():
    #Check for Authorization
    co_auth=request.headers.get('Authorization', None)

    if not co_auth:
        raise AuthError({
            'code': '401 Unauthorized',
            'description': 'You are not authorized, Header missing'
        }, 401) 

    #Split bearer and the token
    co_bearer_split=co_auth.split(' ')

    if len(co_bearer_split) != 2 or not co_bearer_split:
        raise AuthError({
            'code': '401 Unauthorized',
            'description': 'You are not authorized to make this request.'
        }, 401)
    
    elif len(co_bearer_split) == 1:
        raise AuthError({
            'code': '401 Unauthorized',
            'description': 'Token not found'
        }, 401)

    elif len(co_bearer_split) > 2:
        raise AuthError({
            'code': '401 Unauthorized',
            'description': 'Invalid Token'
        }, 401)
    
    elif co_bearer_split[0].lower() != 'bearer':
        raise AuthError({
            'code': '401 Unauthorized',
            'description': 'Header didn\'t start with bearer.'
        }, 401)
    
    token = co_bearer_split[1]

    return token

   #raise Exception('Not Implemented')

'''
@TODO implement check_permissions(permission, payload) method
    @INPUTS
        permission: string permission (i.e. 'post:drink')
        payload: decoded jwt payload

    it should raise an AuthError if permissions are not included in the payload
        !!NOTE check your RBAC settings in Auth0
    it should raise an AuthError if the requested permission string is not in the payload permissions array
    return true otherwise
'''
def check_permissions(permission, payload):
    if 'permissions' not in payload:
        raise AuthError({
            'code': '400 Bad Request',
            'description': 'A bad request was made'
        }, 400)
    
    if permission not in payload['permissions']:
        raise AuthError({
            'code': '403 Forbidden',
            'description': 'Your request is forbidden because you don\'t have the permission to perform this task'
        }, 403)

    return True
    
    #raise Exception('Not Implemented')

'''
@TODO implement verify_decode_jwt(token) method
    @INPUTS
        token: a json web token (string)

    it should be an Auth0 token with key id (kid)
    it should verify the token using Auth0 /.well-known/jwks.json
    it should decode the payload from the token
    it should validate the claims
    return the decoded payload

    !!NOTE urlopen has a common certificate error described here: https://stackoverflow.com/questions/50236117/scraping-ssl-certificate-verify-failed-error-for-http-en-wikipedia-org
'''

def verify_decode_jwt(token):
    #https://auth0.com/docs/quickstart/webapp/python/interactive
    #https://auth0.com/docs/secure/tokens/json-web-tokens/validate-json-web-tokens
    #https://auth0.com/docs/secure/tokens/json-web-tokens/json-web-token-claims
    #https://auth0.com/blog/how-to-handle-jwt-in-python/
    #https://auth0.com/docs/quickstart/backend/python/01-authorization

    jsonurl = urlopen(f'https://{AUTH0_DOMAIN}/.well-known/jwks.json')
    jwks = json.loads(jsonurl.read())
    unverified_header = jwt.get_unverified_header(token)
    rsa_key={}

    if 'kid' not in unverified_header:
        raise AuthError({
            'code': '401 Unauthorized',
            'description': 'Authorization malformed.'
        }, 401)

    for key in jwks['keys']:
        if key['kid'] == unverified_header['kid']:
            rsa_key = {
                'kty': key['kty'],
                'kid': key['kid'],
                'use': key['use'],
                'n': key['n'],
                'e': key['e']
            }

    #Verification for RSA Key        
    if rsa_key:
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=ALGORITHMS,
                audience=API_AUDIENCE,
                issuer='https://'+AUTH0_DOMAIN+'/'
            )
            return payload
    
    #Failure during verification of RSA Key  
        except ExpiredSignatureError:
            raise AuthError({
                'code': '401 Unauthorized',
                'description': 'Expired Token.'
            }, 401)

        except JWTError:
            raise AuthError({
                'code': '401 Unauthorized',
                'description': 'Incorrect claims. Please, check the audience and issuer.'
            }, 401)

        except Exception:
            raise AuthError({
                'code': '400 Bad Request',
                'description': 'Unable to parse authentication token.'
            }, 400)
        
    _request_ctx_stack.top.current_user = payload
    
    return verify_decode_jwt(token)

    #raise Exception('Not Implemented')
        


'''
@TODO implement @requires_auth(permission) decorator method
    @INPUTS
        permission: string permission (i.e. 'post:drink')

    it should use the get_token_auth_header method to get the token
    it should use the verify_decode_jwt method to decode the jwt
    it should use the check_permissions method validate claims and check the requested permission
    return the decorator which passes the decoded payload to the decorated method
'''
def requires_auth(permission=''):
    def requires_auth_decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = get_token_auth_header()
            payload = verify_decode_jwt(token)
            check_permissions(permission, payload)
            return f(payload, *args, **kwargs)
        return wrapper
    return requires_auth_decorator
"""
Standardized API response utilities for consistent frontend-backend communication
"""
from flask import jsonify
from datetime import datetime
from typing import Any, Dict, List, Optional

class APIResponse:
    """Standardized API response builder"""
    
    @staticmethod
    def success(data: Any = None, message: str = "Success", status_code: int = 200, meta: Dict = None):
        """Create a successful API response"""
        response = {
            "status": "success",
            "message": message,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if meta:
            response["meta"] = meta
            
        return jsonify(response), status_code
    
    @staticmethod
    def error(message: str, status_code: int = 400, error_code: str = None, details: Dict = None):
        """Create an error API response"""
        response = {
            "status": "error",
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if error_code:
            response["error_code"] = error_code
            
        if details:
            response["details"] = details
            
        return jsonify(response), status_code
    
    @staticmethod
    def processing(message: str = "Processing", progress: float = None, estimated_time: int = None):
        """Create a processing status response"""
        response = {
            "status": "processing",
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if progress is not None:
            response["progress"] = progress
            
        if estimated_time is not None:
            response["estimated_time_seconds"] = estimated_time
            
        return jsonify(response), 202

class ImageProcessingResponse:
    """Specialized responses for image processing workflow"""
    
    @staticmethod
    def processing_started(token: str):
        """Response when image processing starts"""
        return APIResponse.success(
            data={"token": token},
            message="Image processing started successfully"
        )
    
    @staticmethod
    def processing_completed(token: str, preview_url: str):
        """Response when image processing completes"""
        return APIResponse.success(
            data={
                "token": token,
                "preview_url": preview_url,
                "status": "completed"
            },
            message="Image processing completed successfully"
        )
    
    @staticmethod
    def processing_failed(error: str, token: str = None):
        """Response when image processing fails"""
        details = {"token": token} if token else {}
        return APIResponse.error(
            message=f"Image processing failed: {error}",
            error_code="PROCESSING_ERROR",
            details=details,
            status_code=422
        )

class OrderResponse:
    """Specialized responses for order workflow"""
    
    @staticmethod
    def order_created(order_id: str, external_token: str, payment_status: str = "pending"):
        """Response when order is created"""
        return APIResponse.success(
            data={
                "order_id": order_id,
                "external_token": external_token,
                "payment_status": payment_status
            },
            message="Order created successfully"
        )
    
    @staticmethod
    def payment_processed(order_id: str, transaction_id: str, amount: float, gateway: str):
        """Response when payment is processed"""
        return APIResponse.success(
            data={
                "order_id": order_id,
                "transaction_id": transaction_id,
                "amount": amount,
                "gateway": gateway,
                "status": "paid"
            },
            message="Payment processed successfully"
        )
    
    @staticmethod
    def order_failed(error: str, order_id: str = None):
        """Response when order creation fails"""
        details = {"order_id": order_id} if order_id else {}
        return APIResponse.error(
            message=f"Order creation failed: {error}",
            error_code="ORDER_ERROR",
            details=details,
            status_code=422
        )

class ValidationResponse:
    """Responses for validation errors"""
    
    @staticmethod
    def missing_fields(fields: List[str]):
        """Response for missing required fields"""
        return APIResponse.error(
            message="Missing required fields",
            error_code="VALIDATION_ERROR",
            details={"missing_fields": fields},
            status_code=400
        )
    
    @staticmethod
    def invalid_format(field: str, expected: str, received: str):
        """Response for invalid field format"""
        return APIResponse.error(
            message=f"Invalid format for field '{field}'",
            error_code="FORMAT_ERROR",
            details={
                "field": field,
                "expected": expected,
                "received": received
            },
            status_code=400
        )
    
    @staticmethod
    def file_error(error: str):
        """Response for file-related errors"""
        return APIResponse.error(
            message=f"File error: {error}",
            error_code="FILE_ERROR",
            status_code=400
        )

# Health check response
def health_check_response(health_data: Dict):
    """Standardized health check response"""
    all_healthy = all(
        service for service in health_data.values() 
        if isinstance(service, (bool, dict))
    )
    
    status_code = 200 if all_healthy else 503
    message = "System healthy" if all_healthy else "System issues detected"
    
    return APIResponse.success(
        data=health_data,
        message=message,
        status_code=status_code
    )

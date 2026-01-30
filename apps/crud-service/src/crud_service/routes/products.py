"""Product routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from crud_service.auth import User, get_current_user_optional
from crud_service.integrations import get_agent_client
from crud_service.repositories import ProductRepository

router = APIRouter()
product_repo = ProductRepository()
agent_client = get_agent_client()


class ProductResponse(BaseModel):
    """Product response schema."""

    id: str
    name: str
    description: str
    price: float
    category_id: str
    image_url: str | None = None
    in_stock: bool = True


@router.get("/products", response_model=list[ProductResponse])
async def list_products(
    search: str | None = Query(None, description="Search term"),
    category: str | None = Query(None, description="Category filter"),
    limit: int = Query(20, le=100),
    current_user: User | None = Depends(get_current_user_optional),
):
    """
    List products with optional search and filters.
    
    Anonymous users can browse products.
    Authenticated users may get personalized results (via agent).
    """
    if search:
        products = await product_repo.search_by_name(search, limit=limit)
    elif category:
        products = await product_repo.get_by_category(category, limit=limit)
    else:
        # Get all products (TODO: add pagination)
        products = await product_repo.query(
            query="SELECT * FROM c OFFSET 0 LIMIT @limit",
            parameters=[{"name": "@limit", "value": limit}],
        )

    # Optionally enhance with agent recommendations
    if current_user:
        try:
            recommendations = await agent_client.get_user_recommendations(
                user_id=current_user.user_id, category=category
            )
            # TODO: Reorder products based on recommendations
        except Exception:
            pass  # Fallback to default ordering

    return [ProductResponse(**p) for p in products]


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str):
    """Get product details by ID."""
    product = await product_repo.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Optionally get dynamic pricing
    try:
        dynamic_price = await agent_client.calculate_dynamic_pricing(product_id)
        if dynamic_price:
            product["price"] = dynamic_price
    except Exception:
        pass  # Use base price

    return ProductResponse(**product)

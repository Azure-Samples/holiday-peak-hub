import {
  mapAcpProductToUiProduct,
  mapApiProductToUiProduct,
  parsePriceString,
} from '../../lib/utils/productMappers';

const apiProduct = {
  id: 'SKU-1',
  name: 'Test Product',
  description: 'Test description',
  price: 12.5,
  category_id: 'test-category',
  image_url: '/test.png',
  in_stock: true,
  rating: 4.2,
  review_count: 12,
  features: ['Feature A'],
  media: [{ url: '/test.png', type: 'image' }],
};

describe('product mappers', () => {
  test('parsePriceString handles currency and amount', () => {
    expect(parsePriceString('10.99 usd')).toEqual({ amount: 10.99, currency: 'USD' });
  });

  test('mapApiProductToUiProduct maps core fields', () => {
    const mapped = mapApiProductToUiProduct(apiProduct);
    expect(mapped.sku).toBe('SKU-1');
    expect(mapped.title).toBe('Test Product');
    expect(mapped.price).toBe(12.5);
    expect(mapped.inStock).toBe(true);
  });

  test('mapAcpProductToUiProduct maps availability and price', () => {
    const mapped = mapAcpProductToUiProduct({
      item_id: 'SKU-2',
      title: 'ACP Product',
      price: '19.99 usd',
      availability: 'out_of_stock',
      image_url: '/acp.png',
    });
    expect(mapped.sku).toBe('SKU-2');
    expect(mapped.price).toBe(19.99);
    expect(mapped.currency).toBe('USD');
    expect(mapped.inStock).toBe(false);
  });
});

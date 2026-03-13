import apiClient, { handleApiError } from '../api/client';
import API_ENDPOINTS from '../api/endpoints';
import type {
  CatalogProductContract,
  ComposeRecommendationsRequest,
  ComposeRecommendationsResponse,
  CustomerProfileContract,
  PricingOffersRequest,
  PricingOffersResponse,
  RankRecommendationsRequest,
  RankRecommendationsResponse,
} from '../types/api';

export type PersonalizationFlowRequest = {
  customerId: string;
  sku: string;
  quantity?: number;
  maxItems?: number;
};

export type PersonalizationFlowResponse = {
  product: CatalogProductContract;
  profile: CustomerProfileContract;
  offers: PricingOffersResponse;
  ranked: RankRecommendationsResponse;
  composed: ComposeRecommendationsResponse;
};

function buildOfferWeightedScore(offers: PricingOffersResponse): number {
  if (offers.base_price <= 0) {
    return 0.5;
  }

  const discountRatio = Math.max(
    0,
    Math.min((offers.base_price - offers.final_price) / offers.base_price, 1),
  );

  return Math.max(0, Math.min(0.5 + discountRatio * 0.5, 1));
}

export const personalizationService = {
  async getCatalogProduct(sku: string): Promise<CatalogProductContract> {
    try {
      const response = await apiClient.get<CatalogProductContract>(
        API_ENDPOINTS.brandShopping.catalogProduct(sku),
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async getCustomerProfile(customerId: string): Promise<CustomerProfileContract> {
    try {
      const response = await apiClient.get<CustomerProfileContract>(
        API_ENDPOINTS.brandShopping.customerProfile(customerId),
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async getPricingOffers(request: PricingOffersRequest): Promise<PricingOffersResponse> {
    try {
      const response = await apiClient.post<PricingOffersResponse>(
        API_ENDPOINTS.brandShopping.pricingOffers,
        request,
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async rankRecommendations(
    request: RankRecommendationsRequest,
  ): Promise<RankRecommendationsResponse> {
    try {
      const response = await apiClient.post<RankRecommendationsResponse>(
        API_ENDPOINTS.brandShopping.rankRecommendations,
        request,
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async composeRecommendations(
    request: ComposeRecommendationsRequest,
  ): Promise<ComposeRecommendationsResponse> {
    try {
      const response = await apiClient.post<ComposeRecommendationsResponse>(
        API_ENDPOINTS.brandShopping.composeRecommendations,
        request,
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async runFlow(request: PersonalizationFlowRequest): Promise<PersonalizationFlowResponse> {
    const quantity = request.quantity ?? 1;
    const maxItems = request.maxItems ?? 4;

    const [product, profile] = await Promise.all([
      this.getCatalogProduct(request.sku),
      this.getCustomerProfile(request.customerId),
    ]);

    const offers = await this.getPricingOffers({
      customer_id: request.customerId,
      sku: request.sku,
      quantity,
      currency: 'usd',
    });

    const ranked = await this.rankRecommendations({
      customer_id: request.customerId,
      candidates: [{ sku: request.sku, score: buildOfferWeightedScore(offers) }],
    });

    const composed = await this.composeRecommendations({
      customer_id: request.customerId,
      ranked_items: ranked.ranked.map((item) => ({
        sku: item.sku,
        score: item.score,
      })),
      max_items: maxItems,
    });

    return {
      product,
      profile,
      offers,
      ranked,
      composed,
    };
  },
};

export default personalizationService;

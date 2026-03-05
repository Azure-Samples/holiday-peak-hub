import apiClient, { handleApiError } from '../api/client';
import API_ENDPOINTS from '../api/endpoints';
import type {
  AuditEvent,
  ProductReviewDetail,
  ReviewActionRequest,
  ReviewQueueResponse,
  ReviewStatsResponse,
} from '../types/api';

export const truthService = {
  async getReviewQueue(params?: {
    page?: number;
    page_size?: number;
    category?: string;
    min_confidence?: number;
    max_confidence?: number;
    source?: string;
    sort?: 'confidence_asc' | 'confidence_desc' | 'date_asc' | 'date_desc';
  }): Promise<ReviewQueueResponse> {
    try {
      const response = await apiClient.get<ReviewQueueResponse>(
        API_ENDPOINTS.staff.review.queue,
        { params }
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async getReviewStats(): Promise<ReviewStatsResponse> {
    try {
      const response = await apiClient.get<ReviewStatsResponse>(
        API_ENDPOINTS.staff.review.stats
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async getProductReviewDetail(entityId: string): Promise<ProductReviewDetail> {
    try {
      const response = await apiClient.get<ProductReviewDetail>(
        API_ENDPOINTS.staff.review.product(entityId)
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async getAuditHistory(entityId: string): Promise<AuditEvent[]> {
    try {
      const response = await apiClient.get<AuditEvent[]>(
        API_ENDPOINTS.staff.review.audit(entityId)
      );
      return response.data;
    } catch (error) {
      throw handleApiError(error);
    }
  },

  async submitReviewAction(
    proposalId: string,
    action: ReviewActionRequest
  ): Promise<void> {
    try {
      await apiClient.post(
        API_ENDPOINTS.staff.review.action(proposalId),
        action
      );
    } catch (error) {
      throw handleApiError(error);
    }
  },
};

export default truthService;

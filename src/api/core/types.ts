export interface PageResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface AdminPageResponse<T> extends PageResponse<T> {
  total_pages: number
  has_more: boolean
}

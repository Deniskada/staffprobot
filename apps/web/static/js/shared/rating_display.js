/**
 * JavaScript для отображения рейтингов в системе отзывов.
 * Поддерживает звездные рейтинги, статистику и различные форматы отображения.
 */

class RatingDisplay {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`Container with id "${containerId}" not found`);
            return;
        }
        
        this.options = {
            targetType: options.targetType || null,
            targetId: options.targetId || null,
            showStatistics: options.showStatistics || false,
            showReviewsCount: options.showReviewsCount || true,
            size: options.size || 'medium', // 'small', 'medium', 'large'
            interactive: options.interactive || false,
            onRatingClick: options.onRatingClick || null,
            ...options
        };
        
        this.rating = null;
        this.statistics = null;
        
        this.init();
    }
    
    async init() {
        if (this.options.targetType && this.options.targetId) {
            await this.loadRating();
        }
        
        this.render();
    }
    
    async loadRating() {
        try {
            const response = await fetch(`/api/ratings/${this.options.targetType}/${this.options.targetId}`);
            const result = await response.json();
            
            if (result.success) {
                this.rating = result.rating;
                this.statistics = result.rating.statistics;
                this.render();
            } else {
                console.error('Failed to load rating:', result.message);
            }
        } catch (error) {
            console.error('Error loading rating:', error);
        }
    }
    
    async loadStatistics() {
        if (!this.options.targetType || !this.options.targetId) return;
        
        try {
            const response = await fetch(`/api/ratings/statistics/${this.options.targetType}/${this.options.targetId}`);
            const result = await response.json();
            
            if (result.success) {
                this.statistics = result.statistics;
                this.renderStatistics();
            }
        } catch (error) {
            console.error('Error loading statistics:', error);
        }
    }
    
    render() {
        if (!this.rating) {
            this.container.innerHTML = '<div class="rating-loading">Загрузка рейтинга...</div>';
            return;
        }
        
        const stars = this.createStars();
        const ratingInfo = this.createRatingInfo();
        
        this.container.innerHTML = `
            <div class="rating-display ${this.options.size}">
                <div class="rating-stars">${stars}</div>
                <div class="rating-info">${ratingInfo}</div>
                ${this.options.showStatistics ? '<div class="rating-statistics"></div>' : ''}
            </div>
        `;
        
        if (this.options.showStatistics) {
            this.renderStatistics();
        }
        
        if (this.options.interactive) {
            this.bindInteractiveEvents();
        }
    }
    
    createStars() {
        if (!this.rating || !this.rating.stars) {
            return '<div class="stars-placeholder">Нет рейтинга</div>';
        }
        
        const stars = this.rating.stars;
        let starsHTML = '';
        
        // Полные звезды
        for (let i = 0; i < stars.full_stars; i++) {
            starsHTML += `<i class="fas fa-star star-full" data-rating="${i + 1}"></i>`;
        }
        
        // Половина звезды
        if (stars.has_half_star) {
            starsHTML += `<i class="fas fa-star-half-alt star-half" data-rating="${stars.full_stars + 1}"></i>`;
        }
        
        // Пустые звезды
        for (let i = 0; i < stars.empty_stars; i++) {
            const ratingValue = stars.full_stars + (stars.has_half_star ? 1 : 0) + i + 1;
            starsHTML += `<i class="far fa-star star-empty" data-rating="${ratingValue}"></i>`;
        }
        
        return starsHTML;
    }
    
    createRatingInfo() {
        if (!this.rating) return '';
        
        const rating = this.rating.average_rating;
        const reviewsCount = this.rating.total_reviews;
        
        let infoHTML = `<div class="rating-value">${rating.toFixed(1)}</div>`;
        
        if (this.options.showReviewsCount && reviewsCount > 0) {
            const reviewsText = this.getReviewsText(reviewsCount);
            infoHTML += `<div class="reviews-count">${reviewsText}</div>`;
        }
        
        return infoHTML;
    }
    
    renderStatistics() {
        if (!this.statistics) return;
        
        const statsContainer = this.container.querySelector('.rating-statistics');
        if (!statsContainer) return;
        
        const distribution = this.createDistributionChart();
        const recentInfo = this.createRecentInfo();
        
        statsContainer.innerHTML = `
            <div class="rating-stats">
                <div class="stats-header">
                    <h6>Статистика рейтинга</h6>
                </div>
                <div class="stats-content">
                    ${distribution}
                    ${recentInfo}
                </div>
            </div>
        `;
    }
    
    createDistributionChart() {
        const distribution = this.statistics.rating_distribution;
        const total = this.statistics.total_reviews;
        
        if (total === 0) {
            return '<div class="distribution-empty">Нет отзывов</div>';
        }
        
        let chartHTML = '<div class="distribution-chart">';
        
        // Обратный порядок (5 звезд сверху)
        for (let star = 5; star >= 1; star--) {
            const count = distribution[star] || 0;
            const percentage = total > 0 ? (count / total) * 100 : 0;
            
            chartHTML += `
                <div class="distribution-row">
                    <div class="star-label">
                        ${star} <i class="fas fa-star"></i>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${percentage}%"></div>
                    </div>
                    <div class="count-label">${count}</div>
                </div>
            `;
        }
        
        chartHTML += '</div>';
        return chartHTML;
    }
    
    createRecentInfo() {
        const recent = this.statistics.recent_reviews;
        
        if (recent === 0) {
            return '<div class="recent-info">Нет новых отзывов за последний месяц</div>';
        }
        
        return `
            <div class="recent-info">
                <i class="fas fa-clock"></i>
                ${recent} ${this.getReviewsText(recent)} за последний месяц
            </div>
        `;
    }
    
    getReviewsText(count) {
        if (count === 1) return 'отзыв';
        if (count >= 2 && count <= 4) return 'отзыва';
        return 'отзывов';
    }
    
    bindInteractiveEvents() {
        const stars = this.container.querySelectorAll('.rating-stars i[data-rating]');
        
        stars.forEach(star => {
            star.addEventListener('mouseenter', (e) => {
                if (!this.options.interactive) return;
                this.highlightStars(parseInt(e.target.dataset.rating));
            });
            
            star.addEventListener('mouseleave', () => {
                if (!this.options.interactive) return;
                this.resetStarsHighlight();
            });
            
            star.addEventListener('click', (e) => {
                if (!this.options.interactive) return;
                const rating = parseInt(e.target.dataset.rating);
                if (this.options.onRatingClick) {
                    this.options.onRatingClick(rating);
                }
            });
        });
    }
    
    highlightStars(rating) {
        const stars = this.container.querySelectorAll('.rating-stars i[data-rating]');
        
        stars.forEach(star => {
            const starRating = parseInt(star.dataset.rating);
            star.classList.remove('highlighted');
            
            if (starRating <= rating) {
                star.classList.add('highlighted');
            }
        });
    }
    
    resetStarsHighlight() {
        const stars = this.container.querySelectorAll('.rating-stars i');
        stars.forEach(star => star.classList.remove('highlighted'));
    }
    
    updateRating(newRating) {
        this.rating = newRating;
        this.render();
    }
    
    showLoading() {
        this.container.innerHTML = '<div class="rating-loading">Загрузка рейтинга...</div>';
    }
    
    showError(message) {
        this.container.innerHTML = `<div class="rating-error">Ошибка: ${message}</div>`;
    }
}

// Утилитарные функции для работы с рейтингами
class RatingUtils {
    static formatRating(rating) {
        return parseFloat(rating).toFixed(1);
    }
    
    static getRatingText(rating) {
        const numRating = parseFloat(rating);
        
        if (numRating >= 4.5) return 'Отлично';
        if (numRating >= 3.5) return 'Хорошо';
        if (numRating >= 2.5) return 'Удовлетворительно';
        if (numRating >= 1.5) return 'Плохо';
        return 'Очень плохо';
    }
    
    static getRatingColor(rating) {
        const numRating = parseFloat(rating);
        
        if (numRating >= 4.5) return '#28a745'; // Зеленый
        if (numRating >= 3.5) return '#17a2b8'; // Голубой
        if (numRating >= 2.5) return '#ffc107'; // Желтый
        if (numRating >= 1.5) return '#fd7e14'; // Оранжевый
        return '#dc3545'; // Красный
    }
    
    static createStarRating(rating, size = 'medium') {
        const numRating = parseFloat(rating);
        const fullStars = Math.floor(numRating);
        const hasHalfStar = (numRating - fullStars) >= 0.5;
        const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);
        
        let starsHTML = '';
        
        // Полные звезды
        for (let i = 0; i < fullStars; i++) {
            starsHTML += `<i class="fas fa-star star-full ${size}"></i>`;
        }
        
        // Половина звезды
        if (hasHalfStar) {
            starsHTML += `<i class="fas fa-star-half-alt star-half ${size}"></i>`;
        }
        
        // Пустые звезды
        for (let i = 0; i < emptyStars; i++) {
            starsHTML += `<i class="far fa-star star-empty ${size}"></i>`;
        }
        
        return starsHTML;
    }
    
    static async loadMultipleRatings(targets) {
        try {
            const response = await fetch('/api/ratings/batch', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(targets)
            });
            
            const result = await response.json();
            
            if (result.success) {
                return result.ratings;
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            console.error('Error loading multiple ratings:', error);
            return {};
        }
    }
    
    static async getTopRated(targetType, limit = 10) {
        try {
            const response = await fetch(`/api/ratings/top/${targetType}?limit=${limit}`);
            const result = await response.json();
            
            if (result.success) {
                return result.top_ratings;
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            console.error('Error loading top rated:', error);
            return [];
        }
    }
}

// Глобальные функции для удобства использования
window.RatingDisplay = RatingDisplay;
window.RatingUtils = RatingUtils;

// Инициализация рейтингов при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Инициализируем все элементы с классом rating-container
    const ratingContainers = document.querySelectorAll('.rating-container');
    
    ratingContainers.forEach(container => {
        const targetType = container.dataset.targetType;
        const targetId = container.dataset.targetId;
        const showStats = container.dataset.showStats === 'true';
        const size = container.dataset.size || 'medium';
        const interactive = container.dataset.interactive === 'true';
        
        if (targetType && targetId) {
            new RatingDisplay(container.id, {
                targetType: targetType,
                targetId: parseInt(targetId),
                showStatistics: showStats,
                size: size,
                interactive: interactive
            });
        }
    });
});

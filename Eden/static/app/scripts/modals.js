// modals.js
import { initCharts } from './charts.js';

/**
 * Affiche (ou crée) un modal et charge éventuellement son contenu via AJAX.
 */
export function showModal(modalId, url) {
    console.log(`showModal called with modalId: ${modalId}, url: ${url}`);

    let $modal = $(`#${modalId}`);

    // Créer le HTML du modal s'il n'existe pas déjà
    if (!$modal.length) {
        console.log(`Creating modal with ID: ${modalId}`);
        const modalHTML = `
            <div class="modal fade" id="${modalId}" tabindex="-1" aria-labelledby="${modalId}Label" aria-hidden="true" data-url="${url || ''}">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <button type="button" class="btn-close close" data-dismiss="modal" aria-label="Fermer"></button>
                        </div>
                        <div class="modal-body">
                            <!-- Spinner initialisé ici -->
                            <div class="d-flex justify-content-center align-items-center" style="min-height: 200px;">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="visually-hidden">Chargement...</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>`;
        $('body').append(modalHTML);
        $modal = $(`#${modalId}`);
        console.log(`Modal with ID: ${modalId} created.`);
    } else {
        console.log(`Modal with ID: ${modalId} already exists.`);
        // Réinitialiser le contenu du modal avec le spinner si une URL est fournie
        const $modalContent = $modal.find('.modal-body');
        if (url) {
            $modalContent.html(`
                <div class="d-flex justify-content-center align-items-center" style="min-height: 200px;">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Chargement...</span>
                    </div>
                </div>
            `);
        }
    }

    const modalElement = document.getElementById(modalId);
    const modalInstance = new bootstrap.Modal(modalElement);
    const $modalContent = $modal.find('.modal-body');

    // Afficher le modal immédiatement
    modalInstance.show();

    if (url) {
        console.log(`Loading modal content from URL: ${url}`);
        // Charger le contenu via AJAX
        $.ajax({
            url,
            type: 'GET',
            success: (data) => {
                console.log('Modal content loaded successfully.');
                $modalContent.html(data);
            },
            error: (jqXHR, textStatus, errorThrown) => {
                console.error(`Error loading modal content: ${textStatus}, ${errorThrown}`);
                $modalContent.html(`
                    <div class="alert alert-danger" role="alert">
                        Une erreur est survenue lors du chargement des détails.
                    </div>
                `);
            }
        });
    } else {
        console.log('No URL provided. Showing modal without loading content.');
    }

    // Mettre à jour l'attribut data-url
    $modal.attr('data-url', url || '');

    // Supprimer le modal du DOM lorsqu'il est caché
    $modal.off('hidden.bs.modal').on('hidden.bs.modal', function () {
        console.log(`Modal with ID: ${modalId} has been hidden and will be removed.`);
        $(this).remove();
    });
}

/**
 * Sauvegarde l'état d'un modal spécifique.
 */
export function saveModalState(modalId, url) {
    const storageKey = `pageState_${window.location.pathname}`;
    const state = JSON.parse(localStorage.getItem(storageKey)) || { carousels: {}, modals: [] };
    
    const existingModalIndex = state.modals.findIndex(modal => modal.id === modalId);
    if (existingModalIndex !== -1) {
        state.modals[existingModalIndex].url = url;
    } else {
        state.modals.push({ id: modalId, url });
    }
    localStorage.setItem(storageKey, JSON.stringify(state));
}

/**
 * Ferme et supprime le modal du DOM.
 */
export function hideForm(modalId) {
    const modalElement = document.getElementById(modalId);
    if (modalElement) {
        modalElement.remove();
    }
}
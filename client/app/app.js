'use strict';

angular.module('scotusChatApp', [
  'ngCookies',
  'ngResource',
  'ngSanitize',
  'ngMaterial',
  'angularMoment',
  'ui.router'
])
  .config(function ($stateProvider, $urlRouterProvider, $locationProvider, $httpProvider) {
    $urlRouterProvider
      .otherwise('/');

    $locationProvider.html5Mode(true);
    $httpProvider.interceptors.push('authInterceptor');
  })
  .config(function($mdThemingProvider) {
    $mdThemingProvider.theme('default')
      .primaryPalette('cyan')
      .accentPalette('pink')
      .backgroundPalette('grey', {'default':'100'});
  })
  .factory('Nav', ['$rootScope', function($rootScope){
  
  var savedParams = {};

  $rootScope.$on('$stateChangeStart', function(event, toState, toParams, fromState, fromParams){
    savedParams = toParams;
  });

  return function Nav(){
    this.getSavedParams = function() {
      console.debug('Loading last params');
      console.log(savedParams);
      return savedParams;
    };
  };
}])
  
  .factory('authInterceptor', function ($rootScope, $q, $cookieStore, $location) {
    return {
      // Add authorization token to headers
      request: function (config) {
        config.headers = config.headers || {};
        if ($cookieStore.get('token')) {
          config.headers.Authorization = 'Bearer ' + $cookieStore.get('token');
        }
        return config;
      },

      // Intercept 401s and redirect you to login
      responseError: function(response) {
        if(response.status === 401) {
          $location.path('/login');
          // remove any stale tokens
          $cookieStore.remove('token');
          return $q.reject(response);
        }
        else {
          return $q.reject(response);
        }
      }
    };
  })

  .run(function ($rootScope, $location, Auth) {
    // Redirect to login if route requires auth and you're not logged in
    $rootScope.$on('$stateChangeStart', function (event, next) {
      Auth.isLoggedInAsync(function(loggedIn) {
        if (next.authenticate && !loggedIn) {
          event.preventDefault();
          $location.path('/login');
        }
      });
    });
  });

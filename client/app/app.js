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
.factory('$localstorage', ['$window', function($window) {
  return {
    set: function(key, value) {
      $window.localStorage[key] = value;
    },
    get: function(key, defaultValue) {
      return $window.localStorage[key] || 'empty';
    },
    remove: function(key) {
      $window.localStorage.removeItem[key];
    },
    setObject: function(key, value) {
      $window.localStorage[key] = JSON.stringify(value);
    },
    getObject: function(key) {
      return JSON.parse($window.localStorage[key] || '{"available":"nothing"}');
      // return JSON.parse($window.localStorage[key] || '{}');
    },
    removeObject: function(key) {
      $window.localStorage.removeItem[key];
    },
    removeAll: function(){
      localStorage.clear();
    }
  }
}])
  .directive("speaker", ['$localstorage', '$q', '$sce', '$compile', function($localstorage, $q, $sce, $compile) {
    return {
        restrict: 'E',
        replace: true,
        link: function(scope, element, attrs) {
        //   var deferred = $q.defer();
        // deferred.resolve(cache.currentSpeaker);
        // return deferred.promise;
            var cache = $localstorage.getObject('speakersCache');
            var speakerID = attrs.data;
            //scope.message = attrs.message;
            scope.speaker = [];


            if(speakerID == ""){
              console.log('found a room');
              scope.speaker.namefirst = "Room";
              scope.speaker.image = "http://actionzone.actionforpeople.netdna-cdn.com/wp-content/uploads/2015/01/1423424704_icon-ios7-people-128.png";
            }
            else{
              scope.speaker = cache[speakerID];

            }

            scope.messageHTML = $sce.trustAsHtml(attrs.message);

            //var expression = $sce.parseAsHtml(attrs.message);

            // console.log(expression)

            // var getResult = function () {
            //     return expression(scope);
            // };

            // scope.$watch(getResult, function (newValue) {
            //     var linker = $compile(newValue);
            //     //scope.messageHTML = linker(scope);
            //     element.append(linker(scope));
            // });
            
        },
        template: '<div class="message-item speaker-{{speaker.bench || false}}"><div class="speaker"><img ng-src="{{speaker.image}}" /> <div class="name">{{speaker.namefirst}} <br/>{{speaker.namelast}}</div></div><div class="message" ng-bind-html="messageHTML"></div></div>'
    }
  }])

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

'use strict';

angular.module('scotusChatApp')
  .controller('ScotusCtrl', function ($rootScope, $state, $stateParams) {
    $rootScope.$state = $state;
  	$rootScope.$stateParams = $stateParams;
  });

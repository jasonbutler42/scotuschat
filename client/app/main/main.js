'use strict';

angular.module('scotusChatApp')
  .config(function ($stateProvider) {
    $stateProvider
      .state('scotus', {
        abstract: true,
        templateUrl: 'app/scotus/template.html',
        controller: 'ScotusCtrl'
      })      
      .state('scotus.main', {
        url: '/',
        templateUrl: 'app/main/main.html',
        controller: 'MainCtrl'
      });
  });
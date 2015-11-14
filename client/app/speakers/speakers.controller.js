'use strict';

angular.module('scotusChatApp')
  .controller('SpeakersCtrl', function (Nav, API, $rootScope, $scope, $http, $location) {

    API.getSpeakers().then(function(data) {
      $scope.speakers = data;
    });     

});

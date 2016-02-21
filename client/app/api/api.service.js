'use strict';

angular.module('scotusChatApp')


  .service('API', ['$http', '$q', function($http, $q){
  

    // Private API data
    var cache = {
      speakers: [],
      currentSpeaker: null,
      chats: [],
      currentChat: null
    };

    this.getSpeakers = function() {
        return $http.get('/api/speakers/').then(function(response) {
          var speakers = {};
          angular.forEach(response.data, function(value, key){
              speakers[value._id] = value;
              //var newArr = { valID : value};
              //speakers.push(newArr);
          });
          console.log(speakers);
          return speakers;
        });
      };
    
    this.getSpeaker = function(id) {
      if (!cache.currentSpeaker) {
        return $http.get('/api/speakers/'+ id).then(function(response) {
          cache.currentSpeaker = response.data;
          return response.data;
        });
      } else {
        var deferred = $q.defer();
        deferred.resolve(cache.currentSpeaker);
        return deferred.promise;
      }
    };

    this.getChats = function() {
      if (!cache.chats.length) {
        return $http.get('/api/chats/').then(function(response) {
          cache.chats = response.data;
          return response.data;
        });
      } else {
        var deferred = $q.defer();
        deferred.resolve(cache.chats);
        return deferred.promise;
      }
    };

    this.getChat = function(id) {
      if (!cache.currentChat) {
        return $http.get('/api/chats/'+ id).then(function(response) {
          cache.currentChat = response.data;
          return response.data;
        });
      } else {
        var deferred = $q.defer();
        deferred.resolve(cache.currentChat);
        return deferred.promise;
      }
    };
     
    return this;
  
}]);
